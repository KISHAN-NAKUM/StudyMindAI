"""
Comprehensive Model Comparison and Calibration Evaluation for StudyMind.
Evaluates Classical Baseline models (Logistic Regression, Random Forest) against Deep Knowledge Tracing (DKT GRU)
on the exact same held-out student test partition, calculating metric tables and calibration statistics.
"""

import os
import sys
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import joblib
import torch
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, log_loss
)
from ml.feature_engineering import split_by_student, extract_causal_features
from ml.dkt_model import DKTGRUModel
from ml.train_dkt import DKTSequenceDataset, collate_fn
from torch.utils.data import DataLoader

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


def compute_calibration_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> dict:
    """
    Computes calibration curve (reliability diagram) and Expected Calibration Error (ECE).
    Divides predicted probabilities into n_bins and compares mean predicted prob with empirical accuracy.
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    bin_data = []

    for lower, upper in zip(bin_lowers, bin_uppers):
        in_bin = (y_prob > lower) & (y_prob <= upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = float(np.mean(y_true[in_bin]))
            bin_conf = float(np.mean(y_prob[in_bin]))
            ece += (bin_size / len(y_true)) * abs(bin_acc - bin_conf)
            bin_data.append({
                "range": f"[{lower:.1f}, {upper:.1f}]",
                "count": int(bin_size),
                "confidence": round(bin_conf, 3),
                "accuracy": round(bin_acc, 3),
                "gap": round(abs(bin_acc - bin_conf), 3)
            })
        else:
            bin_data.append({
                "range": f"[{lower:.1f}, {upper:.1f}]",
                "count": 0,
                "confidence": round(float((lower + upper) / 2), 3),
                "accuracy": 0.0,
                "gap": 0.0
            })

    return {
        "expected_calibration_error": round(float(ece), 4),
        "bins": bin_data
    }


def run_full_evaluation(data_path: str = "data/sample_data.csv") -> dict:
    """Evaluates Baseline models and DKT on identical test students."""
    df = pd.read_csv(data_path)
    train_df, val_df, test_df = split_by_student(df, train_frac=0.70, val_frac=0.15, random_seed=42)

    # 1. Baseline Evaluation
    baseline_payload_path = os.path.join(ARTIFACTS_DIR, "baseline_model.joblib")
    if not os.path.exists(baseline_payload_path):
        from ml.train_baseline import train_baselines
        train_baselines(data_path)
    
    baseline_payload = joblib.load(baseline_payload_path)
    scaler = baseline_payload["scaler"]
    lr_model = baseline_payload["lr_model"]
    rf_model = baseline_payload["rf_model"]

    X_test, y_test_df = extract_causal_features(test_df)
    y_test = y_test_df.values
    X_test_scaled = scaler.transform(X_test)

    # 0. Trivial Baseline (Majority-Class / Training-Mean)
    p_train = float(train_df["is_correct"].mean())
    majority_class = int(p_train >= 0.5)
    trivial_probs = np.full_like(y_test, p_train, dtype=float)
    trivial_preds = np.full_like(y_test, majority_class, dtype=int)
    trivial_calib = compute_calibration_curve(y_test, trivial_probs)
    trivial_metrics = {
        "model": "Majority-Class / Training-Mean (Trivial Baseline)",
        "accuracy": round(float(accuracy_score(y_test, trivial_preds)), 4),
        "precision": round(float(precision_score(y_test, trivial_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, trivial_preds, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, trivial_preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, trivial_probs)), 4),
        "log_loss": round(float(log_loss(y_test, trivial_probs)), 4),
        "ece": trivial_calib["expected_calibration_error"]
    }

    # LR
    lr_probs = lr_model.predict_proba(X_test_scaled)[:, 1]
    lr_preds = (lr_probs >= 0.5).astype(int)
    lr_calib = compute_calibration_curve(y_test, lr_probs)
    lr_metrics = {
        "model": "Logistic Regression (Baseline)",
        "accuracy": round(float(accuracy_score(y_test, lr_preds)), 4),
        "precision": round(float(precision_score(y_test, lr_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, lr_preds, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, lr_preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, lr_probs)), 4),
        "log_loss": round(float(log_loss(y_test, lr_probs)), 4),
        "ece": lr_calib["expected_calibration_error"]
    }

    # RF
    rf_probs = rf_model.predict_proba(X_test)[:, 1]
    rf_preds = (rf_probs >= 0.5).astype(int)
    rf_calib = compute_calibration_curve(y_test, rf_probs)
    rf_metrics = {
        "model": "Random Forest (Baseline)",
        "accuracy": round(float(accuracy_score(y_test, rf_preds)), 4),
        "precision": round(float(precision_score(y_test, rf_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, rf_preds, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, rf_preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, rf_probs)), 4),
        "log_loss": round(float(log_loss(y_test, rf_probs)), 4),
        "ece": rf_calib["expected_calibration_error"]
    }

    # 2. DKT GRU Evaluation
    dkt_path = os.path.join(ARTIFACTS_DIR, "dkt_model.pt")
    dkt_metrics = None
    dkt_calib = None

    if os.path.exists(dkt_path):
        model = DKTGRUModel(num_skills=15, embed_dim=64, hidden_dim=64, num_layers=1, dropout=0.2)
        weights = torch.load(dkt_path, map_location="cpu")
        model.load_state_dict(weights)
        model.eval()

        test_ds = DKTSequenceDataset(test_df, num_skills=15)
        test_loader = DataLoader(test_ds, batch_size=16, shuffle=False, collate_fn=collate_fn)

        criterion = torch.nn.BCEWithLogitsLoss(reduction='none')
        all_probs = []
        all_targets = []

        with torch.no_grad():
            for in_seq, tgt_skill, tgt_label, mask in test_loader:
                logits = model(in_seq)
                pred_logits = logits.gather(2, tgt_skill.unsqueeze(2)).squeeze(2)
                probs = torch.sigmoid(pred_logits)

                v_mask = mask.numpy()
                probs_np = probs.numpy()
                tgt_np = tgt_label.numpy()

                for b in range(len(v_mask)):
                    m = v_mask[b]
                    all_probs.extend(probs_np[b][m])
                    all_targets.extend(tgt_np[b][m])

        dkt_true = np.array(all_targets)
        dkt_prob = np.array(all_probs)
        dkt_pred = (dkt_prob >= 0.5).astype(int)

        dkt_calib = compute_calibration_curve(dkt_true, dkt_prob)
        dkt_metrics = {
            "model": "Deep Knowledge Tracing (GRU)",
            "accuracy": round(float(accuracy_score(dkt_true, dkt_pred)), 4),
            "precision": round(float(precision_score(dkt_true, dkt_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(dkt_true, dkt_pred, zero_division=0)), 4),
            "f1_score": round(float(f1_score(dkt_true, dkt_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(dkt_true, dkt_prob)), 4),
            "log_loss": round(float(log_loss(dkt_true, dkt_prob)), 4),
            "ece": dkt_calib["expected_calibration_error"]
        }

    comparison = {
        "evaluation_summary": {
            "test_students": int(test_df["student_id"].nunique()),
            "held_out_interactions": len(y_test)
        },
        "models": [trivial_metrics, lr_metrics, rf_metrics] + ([dkt_metrics] if dkt_metrics else []),
        "calibration": {
            "trivial_baseline": trivial_calib,
            "logistic_regression": lr_calib,
            "random_forest": rf_calib,
            "dkt_gru": dkt_calib
        }
    }

    with open(os.path.join(ARTIFACTS_DIR, "model_comparison.json"), "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    return comparison


if __name__ == "__main__":
    comp = run_full_evaluation()
    print("\n--- Model Comparison Summary ---")
    for m in comp["models"]:
        print(f"{m['model']}: Acc={m['accuracy']}, F1={m['f1_score']}, AUC={m['roc_auc']}, LogLoss={m['log_loss']}, ECE={m['ece']}")
