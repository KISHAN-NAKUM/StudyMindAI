"""
Training pipeline for StudyMind Classical ML Baseline models.
Trains Logistic Regression and Random Forest using causal prior features
and evaluates on a held-out student test partition.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, log_loss
)
from ml.feature_engineering import split_by_student, extract_causal_features, FEATURE_NAMES

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """Computes all academic evaluation metrics."""
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "log_loss": round(float(log_loss(y_true, y_prob)), 4)
    }


def train_baselines(data_path: str = "data/sample_data.csv") -> dict:
    """Loads dataset, trains baseline models on leakage-safe student split, and saves artifacts."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    if not os.path.exists(data_path):
        from ml.dataset_generator import generate_synthetic_dataset
        print(f"Data file not found at {data_path}. Generating benchmark dataset...")
        generate_synthetic_dataset(output_path=data_path)

    df = pd.read_csv(data_path)
    train_df, val_df, test_df = split_by_student(df, train_frac=0.70, val_frac=0.15, random_seed=42)

    print(f"Dataset split: Train={len(train_df)} ({train_df['student_id'].nunique()} students), "
          f"Val={len(val_df)} ({val_df['student_id'].nunique()} students), "
          f"Test={len(test_df)} ({test_df['student_id'].nunique()} students)")

    X_train, y_train = extract_causal_features(train_df)
    X_val, y_val = extract_causal_features(val_df)
    X_test, y_test = extract_causal_features(test_df)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # 1. Logistic Regression
    lr = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    lr.fit(X_train_scaled, y_train)

    lr_test_probs = lr.predict_proba(X_test_scaled)[:, 1]
    lr_test_preds = (lr_test_probs >= 0.5).astype(int)
    lr_metrics = compute_metrics(y_test.values, lr_test_preds, lr_test_probs)

    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)  # Tree models don't require scaling

    rf_test_probs = rf.predict_proba(X_test)[:, 1]
    rf_test_preds = (rf_test_probs >= 0.5).astype(int)
    rf_metrics = compute_metrics(y_test.values, rf_test_preds, rf_test_probs)

    # Pick best baseline based on ROC-AUC
    best_model_name = "RandomForest" if rf_metrics["roc_auc"] >= lr_metrics["roc_auc"] else "LogisticRegression"
    best_model = rf if best_model_name == "RandomForest" else lr

    results = {
        "split_summary": {
            "total_students": int(df["student_id"].nunique()),
            "total_interactions": len(df),
            "train_students": int(train_df["student_id"].nunique()),
            "test_students": int(test_df["student_id"].nunique()),
            "feature_names": FEATURE_NAMES
        },
        "logistic_regression": lr_metrics,
        "random_forest": rf_metrics,
        "selected_baseline": best_model_name
    }

    # Save artifacts
    model_payload = {
        "model_name": best_model_name,
        "model": best_model,
        "scaler": scaler,
        "feature_names": FEATURE_NAMES,
        "rf_model": rf,
        "lr_model": lr
    }
    joblib.dump(model_payload, os.path.join(ARTIFACTS_DIR, "baseline_model.joblib"))

    with open(os.path.join(ARTIFACTS_DIR, "baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n--- Baseline Model Evaluation on Held-Out Students ---")
    print("Logistic Regression:", lr_metrics)
    print("Random Forest:      ", rf_metrics)
    print(f"Selected Best Baseline: {best_model_name}")

    return results


if __name__ == "__main__":
    train_baselines()
