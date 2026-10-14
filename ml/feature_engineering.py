"""
Leakage-Safe Feature Engineering for StudyMind Baseline Models.
Extracts strictly causal prior-interaction features and ensures student-level partitioning.
"""

from collections import deque, defaultdict
from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = [
    "prior_total_attempts",
    "prior_total_accuracy",
    "prior_skill_attempts",
    "prior_skill_accuracy",
    "recent_5_accuracy",
    "skill_recent_3_accuracy",
    "difficulty_num",
    "skill_id"
]


def split_by_student(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions dataset strictly by unique student_id to prevent data leakage.
    Ensures that no student appears in more than one partition.
    """
    students = np.array(sorted(df["student_id"].unique()))
    np.random.seed(random_seed)
    np.random.shuffle(students)

    n_students = len(students)
    n_train = int(n_students * train_frac)
    n_val = int(n_students * val_frac)

    train_ids = set(students[:n_train])
    val_ids = set(students[n_train:n_train + n_val])
    test_ids = set(students[n_train + n_val:])

    train_df = df[df["student_id"].isin(train_ids)].copy()
    val_df = df[df["student_id"].isin(val_ids)].copy()
    test_df = df[df["student_id"].isin(test_ids)].copy()

    return train_df, val_df, test_df


def extract_causal_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Extracts strictly prior features for each interaction.
    Features at step t depend exclusively on steps 0 through t-1.
    """
    # Ensure chronological ordering
    sorted_df = df.sort_values(by=["student_id", "step_index"]).reset_index(drop=True)

    feature_rows: List[Dict[str, Any]] = []
    labels: List[int] = []

    # Process each student independently
    for student_id, student_group in sorted_df.groupby("student_id", sort=False):
        total_attempts = 0
        total_correct = 0
        recent_window = deque(maxlen=5)
        skill_attempts = defaultdict(int)
        skill_correct = defaultdict(int)
        skill_recent = defaultdict(lambda: deque(maxlen=3))

        for _, row in student_group.iterrows():
            s_id = int(row["skill_id"])
            diff_num = int(row.get("difficulty_num", 2))
            actual_correct = int(row["is_correct"])

            # 1. Compute features using PRIOR state only
            prior_tot_acc = (total_correct / total_attempts) if total_attempts > 0 else 0.5
            s_att = skill_attempts[s_id]
            prior_s_acc = (skill_correct[s_id] / s_att) if s_att > 0 else 0.5
            rec_acc = (sum(recent_window) / len(recent_window)) if len(recent_window) > 0 else 0.5
            s_rec = skill_recent[s_id]
            s_rec_acc = (sum(s_rec) / len(s_rec)) if len(s_rec) > 0 else 0.5

            feature_rows.append({
                "prior_total_attempts": total_attempts,
                "prior_total_accuracy": prior_tot_acc,
                "prior_skill_attempts": s_att,
                "prior_skill_accuracy": prior_s_acc,
                "recent_5_accuracy": rec_acc,
                "skill_recent_3_accuracy": s_rec_acc,
                "difficulty_num": diff_num,
                "skill_id": s_id
            })
            labels.append(actual_correct)

            # 2. Update state with current observation
            total_attempts += 1
            if actual_correct == 1:
                total_correct += 1
            recent_window.append(actual_correct)
            skill_attempts[s_id] += 1
            if actual_correct == 1:
                skill_correct[s_id] += 1
            skill_recent[s_id].append(actual_correct)

    X = pd.DataFrame(feature_rows)[FEATURE_NAMES]
    y = pd.Series(labels, name="is_correct")
    return X, y
