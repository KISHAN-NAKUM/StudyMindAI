"""
Inference and Knowledge State Prediction for StudyMind.
Provides real-time student mastery estimations using trained DKT GRU or Baseline models
fed by live SQLite student response records.
"""

import os
import joblib
import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from database.db import DatabaseManager
from ml.dkt_model import DKTGRUModel
from ml.feature_engineering import FEATURE_NAMES

from ml.skill_map import TOPIC_NAME_TO_SKILL

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


class KnowledgePredictor:
    """Predicts student skill mastery and next-question success probabilities."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.dkt_model: Optional[DKTGRUModel] = None
        self.baseline_payload: Optional[dict] = None
        self._load_models()

    def _load_models(self) -> None:
        """Loads available trained model weights without crashing if uninitialized."""
        # 1. Load Baseline
        baseline_path = os.path.join(ARTIFACTS_DIR, "baseline_model.joblib")
        if os.path.exists(baseline_path):
            try:
                self.baseline_payload = joblib.load(baseline_path)
            except Exception as e:
                print(f"[StudyMind Predictor] Could not load baseline model: {e}")

        # 2. Load DKT GRU
        dkt_path = os.path.join(ARTIFACTS_DIR, "dkt_model.pt")
        if os.path.exists(dkt_path):
            try:
                model = DKTGRUModel(num_skills=15, embed_dim=64, hidden_dim=64, num_layers=1, dropout=0.2)
                weights = torch.load(dkt_path, map_location="cpu")
                model.load_state_dict(weights)
                model.eval()
                self.dkt_model = model
            except Exception as e:
                print(f"[StudyMind Predictor] Could not load DKT model: {e}")

    def predict_topic_mastery(
        self,
        student_id: int,
        subject_id: int,
        prefer_model: str = "dkt"
    ) -> Dict[int, float]:
        """
        Estimates success probability for each topic in the given subject.
        Returns: Dict {topic_id: probability_between_0_and_1}
        """
        topics = self.db.get_topics_by_subject(subject_id)
        if not topics:
            return {}

        interactions = self.db.get_student_chronological_interactions(student_id)

        # 1. Try DKT GRU if available
        if prefer_model == "dkt" and self.dkt_model is not None and interactions:
            try:
                # Convert interaction history to DKT tokens using explicit topic name lookup
                num_skills = self.dkt_model.num_skills
                tokens = []
                for item in interactions[-50:]:  # Last 50 interactions
                    top_name = item.get("topic_name")
                    if not top_name or top_name not in TOPIC_NAME_TO_SKILL:
                        continue
                    s_idx = TOPIC_NAME_TO_SKILL[top_name]
                    if s_idx >= num_skills:
                        continue
                    c = 1 if item["is_correct"] == 1 else 0
                    tok = 1 + s_idx + (c * num_skills)
                    tokens.append(tok)

                if tokens:
                    dkt_probs = self.dkt_model.predict_next_skills(tokens).numpy()
                    topic_preds = {}
                    fallback_stats = None
                    for top in topics:
                        if top.name in TOPIC_NAME_TO_SKILL and TOPIC_NAME_TO_SKILL[top.name] < num_skills:
                            idx = TOPIC_NAME_TO_SKILL[top.name]
                            prob = float(dkt_probs[idx])
                            topic_preds[top.id] = round(max(0.10, min(0.95, prob)), 3)
                        else:
                            # Skip gracefully and use empirical-accuracy fallback
                            if fallback_stats is None:
                                fallback_stats = {s["topic_id"]: s for s in self.db.get_student_topic_stats(student_id, subject_id)}
                            s = fallback_stats.get(top.id)
                            if s and s["attempts"] > 0:
                                topic_preds[top.id] = round(s["accuracy"] / 100.0, 3)
                            else:
                                topic_preds[top.id] = 0.50
                    return topic_preds
            except Exception as e:
                print(f"[StudyMind Predictor] DKT prediction error: {e}")

        # 2. Try Baseline if available
        if self.baseline_payload is not None and interactions:
            try:
                model = self.baseline_payload["model"]
                scaler = self.baseline_payload["scaler"]

                # Extract latest student state
                total_att = len(interactions)
                total_corr = sum(1 for x in interactions if x["is_correct"] == 1)
                tot_acc = total_corr / total_att if total_att > 0 else 0.5
                rec_5 = interactions[-5:]
                rec_acc = sum(1 for x in rec_5 if x["is_correct"] == 1) / len(rec_5) if rec_5 else 0.5

                topic_preds = {}
                fallback_stats = None
                for top in topics:
                    if top.name not in TOPIC_NAME_TO_SKILL:
                        # Skip gracefully and use empirical-accuracy fallback
                        if fallback_stats is None:
                            fallback_stats = {s["topic_id"]: s for s in self.db.get_student_topic_stats(student_id, subject_id)}
                        s = fallback_stats.get(top.id)
                        if s and s["attempts"] > 0:
                            topic_preds[top.id] = round(s["accuracy"] / 100.0, 3)
                        else:
                            topic_preds[top.id] = 0.50
                        continue

                    skill_idx = TOPIC_NAME_TO_SKILL[top.name]
                    t_items = [x for x in interactions if x["topic_id"] == top.id]
                    t_att = len(t_items)
                    t_corr = sum(1 for x in t_items if x["is_correct"] == 1)
                    t_acc = t_corr / t_att if t_att > 0 else 0.5
                    t_rec = t_items[-3:]
                    t_rec_acc = sum(1 for x in t_rec if x["is_correct"] == 1) / len(t_rec) if t_rec else 0.5

                    feat_row = pd.DataFrame([{
                        "prior_total_attempts": total_att,
                        "prior_total_accuracy": tot_acc,
                        "prior_skill_attempts": t_att,
                        "prior_skill_accuracy": t_acc,
                        "recent_5_accuracy": rec_acc,
                        "skill_recent_3_accuracy": t_rec_acc,
                        "difficulty_num": 2,
                        "skill_id": skill_idx
                    }])[FEATURE_NAMES]

                    if self.baseline_payload["model_name"] == "LogisticRegression":
                        feat_scaled = scaler.transform(feat_row)
                        prob = float(model.predict_proba(feat_scaled)[0, 1])
                    else:
                        prob = float(model.predict_proba(feat_row)[0, 1])

                    topic_preds[top.id] = round(max(0.10, min(0.95, prob)), 3)
                return topic_preds
            except Exception as e:
                print(f"[StudyMind Predictor] Baseline prediction error: {e}")

        # 3. Transparent Fallback (Empirical Stats or Cold Start)
        stats = self.db.get_student_topic_stats(student_id, subject_id)
        stat_map = {s["topic_id"]: s for s in stats}

        fallback_preds = {}
        for top in topics:
            s = stat_map.get(top.id)
            if s and s["attempts"] > 0:
                fallback_preds[top.id] = round(s["accuracy"] / 100.0, 3)
            else:
                fallback_preds[top.id] = 0.50  # Neutral cold start

        return fallback_preds
