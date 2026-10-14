"""
Analytics and Learning Intelligence endpoints for StudyMindAI.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from database.db import DatabaseManager, DEFAULT_DB_PATH
from ml.predict import KnowledgePredictor
from quiz.adaptive_selector import AdaptiveTopicSelector

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Mastery"])


@router.get("/overview/{student_id}")
def get_student_overview(student_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    history = db.get_student_quiz_history(student_id)
    all_topic_stats = db.get_student_topic_stats(student_id)
    subjects = db.get_all_subjects()

    total_quizzes = len(history)
    total_questions = sum(h["total_questions"] for h in history)
    total_correct = sum(h["score"] for h in history)
    avg_accuracy = round((total_correct / total_questions * 100), 1) if total_questions > 0 else 0.0

    # Mastered topics: at least 3 attempts and >= 75% accuracy
    mastered_count = sum(1 for t in all_topic_stats if t["attempts"] >= 3 and t["accuracy"] >= 75.0)
    practicing_count = sum(1 for t in all_topic_stats if t["attempts"] > 0 and t["accuracy"] < 75.0)

    # Next best action recommendation
    recommendation = None
    if subjects:
        first_subj = subjects[0]
        predictor = KnowledgePredictor(db)
        selector = AdaptiveTopicSelector(db)
        ml_preds = predictor.predict_topic_mastery(student_id, first_subj.id)
        alloc = selector.get_topic_allocation(student_id, first_subj.id, ml_predictions=ml_preds)
        recommendation = {
            "subject_id": first_subj.id,
            "subject_name": first_subj.name,
            "rationale": alloc["rationale"],
            "suggested_topics": alloc.get("suggested_topics", [])
        }

    return {
        "student_id": student_id,
        "total_quizzes": total_quizzes,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "avg_accuracy": avg_accuracy,
        "mastered_topics": mastered_count,
        "practicing_topics": practicing_count,
        "active_subjects_count": len(subjects),
        "recommendation": recommendation
    }


@router.get("/mastery/{student_id}")
def get_student_mastery(student_id: int, subject_id: Optional[int] = None):
    db = DatabaseManager(DEFAULT_DB_PATH)
    subjects = db.get_all_subjects()
    
    result = []
    target_subjects = [s for s in subjects if subject_id is None or s.id == subject_id]

    for subj in target_subjects:
        topic_stats = db.get_student_topic_stats(student_id, subj.id)
        formatted_topics = []
        for t in topic_stats:
            acc = t.get("accuracy", 0.0)
            attempts = t.get("attempts", 0)
            correct = t.get("correct_count", t.get("correct", 0))
            if attempts == 0:
                status = "Unattempted"
                badge = "neutral"
            elif attempts >= 3 and acc >= 75.0:
                status = "Mastered"
                badge = "success"
            elif acc < 60.0:
                status = "Needs Practice"
                badge = "warning"
            else:
                status = "In Progress"
                badge = "primary"

            formatted_topics.append({
                "topic_id": t["topic_id"],
                "topic_name": t["topic_name"],
                "attempts": attempts,
                "correct": correct,
                "accuracy": acc,
                "status": status,
                "badge": badge
            })

        result.append({
            "subject_id": subj.id,
            "subject_name": subj.name,
            "topics": formatted_topics
        })

    return result


@router.get("/timeline/{student_id}")
def get_student_timeline(student_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    history = db.get_student_quiz_history(student_id)
    timeline = []
    for h in history:
        accuracy = round(h["score"] / h["total_questions"] * 100, 1) if h["total_questions"] > 0 else 0
        timeline.append({
            "session_id": h["id"],
            "date": h["created_at"],
            "subject_name": h["subject_name"],
            "score": h["score"],
            "total_questions": h["total_questions"],
            "accuracy": accuracy,
            "mode": h["mode"]
        })
    return timeline
