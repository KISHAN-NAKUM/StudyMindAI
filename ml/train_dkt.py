"""
Training and evaluation pipeline for Deep Knowledge Tracing (DKT) GRU in StudyMind.
Processes per-student sequential interactions with padding and masking.
"""

import os
import sys
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Tuple, List, Dict
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, log_loss
)
from ml.feature_engineering import split_by_student
from ml.dkt_model import DKTGRUModel

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


class DKTSequenceDataset(Dataset):
    """Dataset packaging student interaction sequences for recurrent training."""

    def __init__(self, df: pd.DataFrame, num_skills: int = 15, max_seq_len: int = 100):
        self.num_skills = num_skills
        self.max_seq_len = max_seq_len
        self.samples = []

        # Group chronologically by student
        sorted_df = df.sort_values(by=["student_id", "step_index"]).reset_index(drop=True)
        for _, group in sorted_df.groupby("student_id", sort=False):
            skills = group["skill_id"].values.astype(int)
            corrects = group["is_correct"].values.astype(int)

            if len(skills) < 2:
                continue

            # Interaction token: 1 + skill + correct * num_skills (1-indexed, 0=padding)
            tokens = 1 + skills + (corrects * num_skills)

            # Input is tokens[:-1], target is (next_skill, next_correct)
            in_tokens = tokens[:-1][:max_seq_len]
            tgt_skills = skills[1:][:max_seq_len]
            tgt_labels = corrects[1:][:max_seq_len]

            self.samples.append({
                "in_tokens": in_tokens,
                "tgt_skills": tgt_skills,
                "tgt_labels": tgt_labels,
                "length": len(in_tokens)
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        return self.samples[idx]


def collate_fn(batch: list) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Pads variable-length sequences to batch max length."""
    max_len = max(item["length"] for item in batch)
    b_size = len(batch)

    in_seq = torch.zeros((b_size, max_len), dtype=torch.long)
    tgt_skill = torch.zeros((b_size, max_len), dtype=torch.long)
    tgt_label = torch.zeros((b_size, max_len), dtype=torch.float32)
    mask = torch.zeros((b_size, max_len), dtype=torch.bool)

    for i, item in enumerate(batch):
        l = item["length"]
        in_seq[i, :l] = torch.tensor(item["in_tokens"], dtype=torch.long)
        tgt_skill[i, :l] = torch.tensor(item["tgt_skills"], dtype=torch.long)
        tgt_label[i, :l] = torch.tensor(item["tgt_labels"], dtype=torch.float32)
        mask[i, :l] = True

    return in_seq, tgt_skill, tgt_label, mask


def train_dkt(
    data_path: str = "data/sample_data.csv",
    num_skills: int = 15,
    epochs: int = 25,
    batch_size: int = 16,
    lr: float = 0.003
) -> dict:
    """Trains DKT GRU model with masked BCE loss and early stopping."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    df = pd.read_csv(data_path)
    train_df, val_df, test_df = split_by_student(df, train_frac=0.70, val_frac=0.15, random_seed=42)

    train_ds = DKTSequenceDataset(train_df, num_skills=num_skills)
    val_ds = DKTSequenceDataset(val_df, num_skills=num_skills)
    test_ds = DKTSequenceDataset(test_df, num_skills=num_skills)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DKTGRUModel(num_skills=num_skills, embed_dim=64, hidden_dim=64, num_layers=1, dropout=0.2).to(device)

    criterion = nn.BCEWithLogitsLoss(reduction='none')
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_loss = float("inf")
    best_weights = None
    patience = 5
    patience_counter = 0

    print(f"Training DKT GRU on {len(train_ds)} student sequences (Device: {device})...")

    for epoch in range(1, epochs + 1):
        model.train()
        total_train_loss = 0.0
        train_tokens = 0

        for in_seq, tgt_skill, tgt_label, mask in train_loader:
            in_seq = in_seq.to(device)
            tgt_skill = tgt_skill.to(device)
            tgt_label = tgt_label.to(device)
            mask = mask.to(device)

            optimizer.zero_grad()
            logits = model(in_seq)  # (B, T, num_skills)

            # Gather target skill logit at each step
            pred_logits = logits.gather(2, tgt_skill.unsqueeze(2)).squeeze(2)  # (B, T)
            loss_mat = criterion(pred_logits, tgt_label)
            masked_loss = (loss_mat * mask.float()).sum()

            valid_count = mask.sum().item()
            if valid_count > 0:
                loss = masked_loss / valid_count
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 10.0)
                optimizer.step()

                total_train_loss += masked_loss.item()
                train_tokens += valid_count

        # Validation
        model.eval()
        val_loss_sum = 0.0
        val_tokens = 0
        with torch.no_grad():
            for in_seq, tgt_skill, tgt_label, mask in val_loader:
                in_seq = in_seq.to(device)
                tgt_skill = tgt_skill.to(device)
                tgt_label = tgt_label.to(device)
                mask = mask.to(device)

                logits = model(in_seq)
                pred_logits = logits.gather(2, tgt_skill.unsqueeze(2)).squeeze(2)
                loss_mat = criterion(pred_logits, tgt_label)
                val_loss_sum += (loss_mat * mask.float()).sum().item()
                val_tokens += mask.sum().item()

        avg_val_loss = val_loss_sum / max(1, val_tokens)
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_weights = {k: v.cpu() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                avg_train_loss = total_train_loss / max(1, train_tokens)
                print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")
                print(f"Early stopping triggered at epoch {epoch:02d} (patience={patience}, best val loss: {best_val_loss:.4f})")
                break

        if epoch % 5 == 0 or epoch == epochs:
            avg_train_loss = total_train_loss / max(1, train_tokens)
            print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

    # Load best weights for test evaluation
    if best_weights:
        model.load_state_dict(best_weights)

    # Test evaluation
    model.eval()
    all_preds = []
    all_targets = []
    all_probs = []

    with torch.no_grad():
        for in_seq, tgt_skill, tgt_label, mask in test_loader:
            in_seq = in_seq.to(device)
            tgt_skill = tgt_skill.to(device)
            tgt_label = tgt_label.to(device)
            mask = mask.to(device)

            logits = model(in_seq)
            pred_logits = logits.gather(2, tgt_skill.unsqueeze(2)).squeeze(2)
            probs = torch.sigmoid(pred_logits)

            valid_mask = mask.cpu().numpy()
            probs_np = probs.cpu().numpy()
            targets_np = tgt_label.cpu().numpy()

            for b in range(len(valid_mask)):
                m = valid_mask[b]
                all_probs.extend(probs_np[b][m])
                all_targets.extend(targets_np[b][m])

    y_true = np.array(all_targets)
    y_prob = np.array(all_probs)
    y_pred = (y_prob >= 0.5).astype(int)

    test_metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "log_loss": round(float(log_loss(y_true, y_prob)), 4),
        "test_interactions_evaluated": len(y_true)
    }

    # Save model and metrics
    torch.save(best_weights, os.path.join(ARTIFACTS_DIR, "dkt_model.pt"))
    with open(os.path.join(ARTIFACTS_DIR, "dkt_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)

    print("\n--- Deep Knowledge Tracing (DKT GRU) Test Evaluation ---")
    print(test_metrics)
    return test_metrics


if __name__ == "__main__":
    train_dkt()
