"""
Tests for StudyMind Machine Learning pipeline.
Verifies leakage-safe student partitioning, strictly causal feature extraction,
and model inference dimensions.
"""

import pytest
import numpy as np
import pandas as pd
import torch
from ml.feature_engineering import split_by_student, extract_causal_features
from ml.dkt_model import DKTGRUModel
from ml.predict import KnowledgePredictor


def test_leakage_safe_student_partitioning():
    # Synthetic small dataframe with 10 students
    records = []
    for s_id in range(1, 11):
        for step in range(10):
            records.append({
                "student_id": s_id,
                "step_index": step,
                "skill_id": s_id % 3,
                "difficulty_num": 2,
                "is_correct": 1 if step % 2 == 0 else 0
            })
    df = pd.DataFrame(records)

    train_df, val_df, test_df = split_by_student(df, train_frac=0.6, val_frac=0.2, random_seed=42)

    train_students = set(train_df["student_id"].unique())
    val_students = set(val_df["student_id"].unique())
    test_students = set(test_df["student_id"].unique())

    # Verify ZERO student overlap
    assert len(train_students.intersection(val_students)) == 0, "Train and Val share students!"
    assert len(train_students.intersection(test_students)) == 0, "Train and Test share students!"
    assert len(val_students.intersection(test_students)) == 0, "Val and Test share students!"


def test_causal_feature_engineering_no_future_leakage():
    # Sequence of 3 steps for 1 student:
    # step 0: incorrect (0)
    # step 1: correct (1)
    # step 2: correct (1)
    df = pd.DataFrame([
        {"student_id": 1, "step_index": 0, "skill_id": 0, "difficulty_num": 2, "is_correct": 0},
        {"student_id": 1, "step_index": 1, "skill_id": 0, "difficulty_num": 2, "is_correct": 1},
        {"student_id": 1, "step_index": 2, "skill_id": 0, "difficulty_num": 2, "is_correct": 1},
    ])

    X, y = extract_causal_features(df)

    # Step 0: prior attempts must be 0
    assert X.iloc[0]["prior_total_attempts"] == 0
    assert X.iloc[0]["prior_total_accuracy"] == 0.5  # default prior

    # Step 1: prior attempts must be 1, prior accuracy must reflect ONLY step 0 (which was 0)
    assert X.iloc[1]["prior_total_attempts"] == 1
    assert X.iloc[1]["prior_total_accuracy"] == 0.0

    # Step 2: prior attempts must be 2, prior accuracy must be 1/2 = 0.5 (from steps 0 and 1)
    assert X.iloc[2]["prior_total_attempts"] == 2
    assert X.iloc[2]["prior_total_accuracy"] == 0.5


def test_dkt_gru_model_forward_pass():
    model = DKTGRUModel(num_skills=15, embed_dim=32, hidden_dim=32, num_layers=1)
    batch_size = 4
    seq_len = 10
    # Dummy interaction tokens between 1 and 30
    dummy_input = torch.randint(1, 30, (batch_size, seq_len), dtype=torch.long)

    logits = model(dummy_input)
    assert logits.shape == (batch_size, seq_len, 15)

    # Test single student inference
    probs = model.predict_next_skills([1, 5, 12])
    assert probs.shape == (15,)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()


def test_topic_to_skill_mapping_completeness(tmp_path):
    from database.seed_data import seed_database
    from database.db import DatabaseManager, init_db
    from ml.skill_map import TOPIC_NAME_TO_SKILL

    temp_db = str(tmp_path / "test_studymind.db")
    init_db(temp_db)
    seed_database(temp_db)

    db = DatabaseManager(temp_db)
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM topics")
    db_topics = [row["name"] for row in cursor.fetchall()]
    conn.close()

    assert len(db_topics) == 15, f"Expected 15 topics in seed database, got {len(db_topics)}"

    # Check every topic in DB has an entry in TOPIC_NAME_TO_SKILL
    for name in db_topics:
        assert name in TOPIC_NAME_TO_SKILL, f"Topic '{name}' missing from TOPIC_NAME_TO_SKILL"

    # Check indices are unique and cover 0-14
    skill_indices = list(TOPIC_NAME_TO_SKILL.values())
    assert len(skill_indices) == len(set(skill_indices)), "Skill indices are not unique"
    assert set(skill_indices) == set(range(15)), f"Skill indices do not cover 0-14: {set(skill_indices)}"


def test_ceiling_analysis_and_trivial_baseline():
    """Verifies that ceiling analysis runs successfully and model comparison includes trivial baseline."""
    from ml.ceiling_analysis import compute_ceiling_metrics
    from ml.evaluate import run_full_evaluation

    res = compute_ceiling_metrics()
    assert "full_test_cohort" in res
    assert "transitions_cohort_dkt_aligned" in res
    assert 0.5 < res["full_test_cohort"]["oracle_auc"] < 1.0
    assert 0.0 < res["full_test_cohort"]["oracle_log_loss"] < 1.0

    eval_res = run_full_evaluation()
    model_names = [m["model"] for m in eval_res["models"]]
    assert any("Trivial Baseline" in m for m in model_names)


