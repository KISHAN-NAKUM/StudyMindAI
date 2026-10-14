"""
Ceiling Analysis (Bayes-Optimal Oracle Benchmark) for StudyMind.
Computes the true Item Response Theory (IRT) success probabilities for every interaction
in the held-out test cohort using the generating generative parameters.
Evaluates the theoretical performance ceiling (maximum achievable AUC and minimum log loss)
on the synthetic student dataset.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

# Ensure project root is in sys.path for direct script invocation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.metrics import roc_auc_score, log_loss, accuracy_score, brier_score_loss
from ml.feature_engineering import split_by_student

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


def compute_ceiling_metrics(data_path: str = "data/sample_data.csv") -> dict:
    """Computes oracle performance metrics on the held-out test cohort."""
    df = pd.read_csv(data_path)
    train_df, val_df, test_df = split_by_student(df, train_frac=0.70, val_frac=0.15, random_seed=42)

    if "true_prob" not in test_df.columns:
        raise ValueError(
            "Column 'true_prob' not found in dataset. Ensure dataset_generator.py "
            "stores 'true_prob' during generation."
        )

    # 1. Full test cohort evaluation (2,771 interactions)
    y_all = test_df["is_correct"].values
    prob_all = test_df["true_prob"].values
    pred_all = (prob_all >= 0.5).astype(int)

    auc_all = float(roc_auc_score(y_all, prob_all))
    loss_all = float(log_loss(y_all, prob_all))
    acc_all = float(accuracy_score(y_all, pred_all))
    brier_all = float(brier_score_loss(y_all, prob_all))

    # 2. Sequential transitions evaluation (2,726 transitions, excluding step 0 per student)
    trans_mask = test_df.groupby("student_id").cumcount() > 0
    test_trans = test_df[trans_mask]
    y_trans = test_trans["is_correct"].values
    prob_trans = test_trans["true_prob"].values
    pred_trans = (prob_trans >= 0.5).astype(int)

    auc_trans = float(roc_auc_score(y_trans, prob_trans))
    loss_trans = float(log_loss(y_trans, prob_trans))
    acc_trans = float(accuracy_score(y_trans, pred_trans))
    brier_trans = float(brier_score_loss(y_trans, prob_trans))

    results = {
        "dataset": data_path,
        "test_students": int(test_df["student_id"].nunique()),
        "full_test_cohort": {
            "total_interactions": len(y_all),
            "oracle_auc": round(auc_all, 4),
            "oracle_log_loss": round(loss_all, 4),
            "oracle_accuracy": round(acc_all, 4),
            "oracle_brier_score": round(brier_all, 4)
        },
        "transitions_cohort_dkt_aligned": {
            "total_transitions": len(y_trans),
            "excluded_first_steps": int((~trans_mask).sum()),
            "oracle_auc": round(auc_trans, 4),
            "oracle_log_loss": round(loss_trans, 4),
            "oracle_accuracy": round(acc_trans, 4),
            "oracle_brier_score": round(brier_trans, 4)
        },
        "theoretical_insight": (
            "Because student responses are stochastic Bernoulli trials with guess rate (0.15), "
            "slip rate (0.05), and logistic noise, the Bayes-optimal oracle upper bound "
            f"on this synthetic dataset is approximately AUC ~ {auc_trans:.4f} and Log Loss ~ {loss_trans:.4f}. "
            "No algorithm can exceed this performance on this data."
        )
    }

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    out_path = os.path.join(ARTIFACTS_DIR, "ceiling_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    res = compute_ceiling_metrics()
    print("=================================================================")
    print("      STUDYMIND THEORETICAL CEILING ANALYSIS (BAYES ORACLE)       ")
    print("=================================================================")
    fc = res["full_test_cohort"]
    tc = res["transitions_cohort_dkt_aligned"]
    print(f"Full Test Interactions (N={fc['total_interactions']}):")
    print(f"  Oracle ROC-AUC  : {fc['oracle_auc']:.4f}")
    print(f"  Oracle Log Loss : {fc['oracle_log_loss']:.4f}")
    print(f"  Oracle Accuracy : {fc['oracle_accuracy']:.4f}")
    print("-----------------------------------------------------------------")
    print(f"Sequential Transitions (N={tc['total_transitions']}, minus {tc['excluded_first_steps']} first steps):")
    print(f"  Oracle ROC-AUC  : {tc['oracle_auc']:.4f}")
    print(f"  Oracle Log Loss : {tc['oracle_log_loss']:.4f}")
    print(f"  Oracle Accuracy : {tc['oracle_accuracy']:.4f}")
    print("=================================================================")
    print(res["theoretical_insight"])
