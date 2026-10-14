"""
Adaptive Topic Selector for StudyMind.
Analyzes student history and machine-learning predictions to construct an optimal
10-question practice distribution emphasizing areas needing practice while retaining revision.
"""

from typing import Dict, List, Any, Optional
from database.db import DatabaseManager


class AdaptiveTopicSelector:
    """Computes topic allocations for student practice sessions."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def get_topic_allocation(
        self,
        student_id: int,
        subject_id: int,
        target_count: int = 10,
        ml_predictions: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """
        Determines the number of questions to pull from each topic.
        Args:
            student_id: ID of the student.
            subject_id: Selected subject ID.
            target_count: Total questions in quiz (standard 10).
            ml_predictions: Optional dict {topic_id: predicted_success_prob} from DKT/Baseline.
        Returns:
            Dict containing:
              - topic_distribution: {topic_id: count} summing to target_count
              - mode: 'diagnostic' or 'adaptive'
              - priority_topics: list of topics prioritized
              - rationale: explanation text for student UI transparency
        """
        topics = self.db.get_topics_by_subject(subject_id)
        if not topics:
            return {
                "topic_distribution": {},
                "mode": "diagnostic",
                "priority_topics": [],
                "rationale": "No topics found for this subject."
            }

        topic_stats = self.db.get_student_topic_stats(student_id, subject_id)
        topic_stats_map = {s["topic_id"]: s for s in topic_stats}

        total_attempts = sum(s["attempts"] for s in topic_stats)

        # 1. Diagnostic / Cold Start Phase
        if total_attempts < 5:
            # Balanced diagnostic distribution
            num_topics = len(topics)
            base_count = target_count // num_topics
            remainder = target_count % num_topics

            distribution = {}
            for i, top in enumerate(topics):
                distribution[top.id] = base_count + (1 if i < remainder else 0)

            return {
                "topic_distribution": distribution,
                "mode": "diagnostic",
                "priority_topics": [],
                "rationale": (
                    "Initial diagnostic baseline: Because you have completed fewer than 5 questions "
                    "in this subject, this quiz provides a balanced diagnostic survey across all topics "
                    "to assess baseline understanding."
                )
            }

        # 2. Adaptive Mode (Student has recorded history)
        # Compute priority score for each topic:
        # Lower accuracy -> higher priority for practice.
        # If ML predictions available: lower predicted success prob -> higher priority.
        scored_topics = []
        for top in topics:
            t_id = top.id
            t_stat = topic_stats_map.get(t_id, {"attempts": 0, "correct_count": 0, "accuracy": 50.0})
            attempts = t_stat["attempts"]
            historical_acc = t_stat["accuracy"] / 100.0 if attempts > 0 else 0.5

            if ml_predictions and t_id in ml_predictions:
                # Weighted combination of ML probability and historical empirical accuracy
                model_prob = ml_predictions[t_id]
                estimated_mastery = 0.6 * model_prob + 0.4 * historical_acc
            else:
                estimated_mastery = historical_acc

            # Priority score: lower mastery means higher need for practice
            # Slight bonus for topics with very few attempts to encourage exploratory practice
            practice_need = 1.0 - estimated_mastery
            if attempts == 0:
                practice_need += 0.2  # exploration bonus

            scored_topics.append({
                "topic_id": t_id,
                "topic_name": top.name,
                "estimated_mastery": round(estimated_mastery * 100, 1),
                "attempts": attempts,
                "practice_need": practice_need
            })

        # Sort descending by practice need
        scored_topics.sort(key=lambda x: x["practice_need"], reverse=True)

        # Allocation strategy:
        # Top 1-2 weakest topics get ~60-70% of questions (e.g., 6 or 7)
        # Remaining topics get ~30-40% for broad revision
        num_topics = len(topics)
        weakest = scored_topics[:max(1, min(2, num_topics))]
        other_topics = scored_topics[len(weakest):]

        focus_allocation = min(7, max(5, target_count - len(other_topics)))
        revision_allocation = target_count - focus_allocation

        distribution = {top.id: 0 for top in topics}

        # Allocate focus questions among weakest
        focus_per_topic = focus_allocation // len(weakest)
        focus_remainder = focus_allocation % len(weakest)
        for i, item in enumerate(weakest):
            distribution[item["topic_id"]] = focus_per_topic + (1 if i < focus_remainder else 0)

        # Allocate revision questions among other topics
        if other_topics:
            rev_per_topic = revision_allocation // len(other_topics)
            rev_remainder = revision_allocation % len(other_topics)
            for i, item in enumerate(other_topics):
                distribution[item["topic_id"]] = rev_per_topic + (1 if i < rev_remainder else 0)
        else:
            # If there's only 1 topic in the whole subject
            distribution[weakest[0]["topic_id"]] += revision_allocation

        # Ensure exact sum of target_count
        current_sum = sum(distribution.values())
        diff = target_count - current_sum
        if diff != 0:
            distribution[weakest[0]["topic_id"]] += diff

        # Generate clear, transparent rationale for student
        priority_names = [f"'{w['topic_name']}' (~{w['estimated_mastery']}% mastery)" for w in weakest]
        rationale = (
            f"Adaptive practice recommendation: Emphasizing {', '.join(priority_names)} "
            f"({focus_allocation} questions) based on your recent learning trends, plus "
            f"{revision_allocation} revision questions from other topics to maintain a balanced curriculum."
        )

        return {
            "topic_distribution": distribution,
            "mode": "adaptive",
            "priority_topics": [w["topic_name"] for w in weakest],
            "rationale": rationale
        }
