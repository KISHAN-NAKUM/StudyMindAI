"""
Quiz Generation, Taking, Grading, and History endpoints for StudyMindAI.
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from database.db import DatabaseManager, DEFAULT_DB_PATH
from database.models import Question
from quiz.generator import QuizGenerator
from quiz.grading import QuizGrader
from quiz.adaptive_selector import AdaptiveTopicSelector
from ml.predict import KnowledgePredictor

router = APIRouter(prefix="/api/quiz", tags=["Quiz Engine"])

# In-memory store for active quiz sessions awaiting submission:
# session_token -> {"questions": [...], "start_time": ..., "subject_id": ..., "subject_name": ..., "mode": ...}
ACTIVE_QUIZ_CACHE: Dict[str, Dict[str, Any]] = {}


class GenerateQuizPayload(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None
    mode: str = "adaptive"  # adaptive or balanced
    difficulty: str = "Medium"
    student_id: Optional[int] = None


class SubmitQuizPayload(BaseModel):
    session_token: str
    student_id: int
    answers: Dict[str, str]  # question index (0..9) or id -> selected option "A", "B", "C", "D"


@router.post("/generate")
def generate_quiz(payload: GenerateQuizPayload):
    db = DatabaseManager(DEFAULT_DB_PATH)
    generator = QuizGenerator(db)
    selector = AdaptiveTopicSelector(db)
    predictor = KnowledgePredictor(db)

    # 1. Look up subject
    subjects = db.get_all_subjects()
    subj = next((s for s in subjects if s.id == payload.subject_id), None)
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")

    is_adaptive = (payload.mode.lower() == "adaptive")
    topic_distribution = None
    rationale = "Balanced diagnostic curriculum survey across topics."

    if is_adaptive and payload.topic_id is None and payload.student_id:
        ml_preds = predictor.predict_topic_mastery(payload.student_id, payload.subject_id)
        alloc = selector.get_topic_allocation(payload.student_id, payload.subject_id, ml_predictions=ml_preds)
        topic_distribution = alloc["topic_distribution"]
        rationale = alloc["rationale"]

    # 2. Generate exactly 10 verified questions
    try:
        raw_questions = generator.generate_quiz(
            subject_id=payload.subject_id,
            topic_id=payload.topic_id,
            difficulty=payload.difficulty,
            topic_distribution=topic_distribution,
            target_count=10,
            student_id=payload.student_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

    if len(raw_questions) < 10:
        raise HTTPException(status_code=500, detail="Could not retrieve 10 valid questions.")

    # 3. Cache the full questions with answer keys server-side
    session_token = f"quiz_{uuid.uuid4().hex}"
    ACTIVE_QUIZ_CACHE[session_token] = {
        "questions": raw_questions,
        "start_time": time.time(),
        "subject_id": payload.subject_id,
        "subject_name": subj.name,
        "mode": payload.mode,
        "difficulty": payload.difficulty,
        "student_id": payload.student_id
    }

    # 4. Strip sensitive answer keys before sending to frontend
    sanitized_questions = []
    for idx, q in enumerate(raw_questions):
        sanitized_questions.append({
            "index": idx,
            "id": q.get("id"),
            "subject_id": q.get("subject_id", payload.subject_id),
            "topic_id": q.get("topic_id", 0),
            "topic": q.get("topic", "General"),
            "difficulty": q.get("difficulty", payload.difficulty),
            "question": q.get("question", ""),
            "options": q.get("options", {}),
            "hint": q.get("hint", "")
        })

    return {
        "session_token": session_token,
        "subject_id": payload.subject_id,
        "subject_name": subj.name,
        "mode": payload.mode,
        "difficulty": payload.difficulty,
        "rationale": rationale,
        "total_questions": len(sanitized_questions),
        "questions": sanitized_questions
    }


@router.post("/submit")
def submit_quiz(payload: SubmitQuizPayload):
    session_data = ACTIVE_QUIZ_CACHE.pop(payload.session_token, None)
    if not session_data:
        raise HTTPException(
            status_code=400,
            detail="Quiz session expired or not found. Please start a new quiz."
        )

    raw_questions = session_data["questions"]
    start_time = session_data["start_time"]
    elapsed_seconds = max(1.0, time.time() - start_time)

    # Convert answers keys to integer indices where appropriate
    parsed_answers = {}
    for k, v in payload.answers.items():
        try:
            parsed_answers[int(k)] = v
        except ValueError:
            parsed_answers[k] = v

    # Grade with QuizGrader
    results = QuizGrader.grade_quiz(
        questions=raw_questions,
        student_answers=parsed_answers,
        elapsed_seconds=elapsed_seconds
    )

    db = DatabaseManager(DEFAULT_DB_PATH)

    # Prepare atomic database responses
    db_responses = []
    for idx, r in enumerate(results["detailed_reviews"]):
        q_id = r.get("question_id")
        t_id = r.get("topic_id")

        if not q_id:
            matching_q = raw_questions[idx] if idx < len(raw_questions) else None
            q_text = r.get("question") or (matching_q.get("question") if matching_q else "")

            if not t_id or t_id == 0:
                subj_topics = db.get_topics_by_subject(session_data["subject_id"])
                t_id = subj_topics[0].id if subj_topics else 1

            conn = db.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM questions WHERE subject_id = ? AND question_text = ?",
                (session_data["subject_id"], q_text)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                q_id = row["id"]
            else:
                opts = r.get("options") or (matching_q.get("options") if matching_q else {})
                new_q = Question(
                    id=None,
                    subject_id=session_data["subject_id"],
                    topic_id=t_id,
                    difficulty=matching_q.get("difficulty", "Medium") if matching_q else "Medium",
                    question_text=q_text,
                    options=opts,
                    correct_answer=r.get("correct_answer", "A"),
                    explanation=r.get("explanation", ""),
                    hint=r.get("hint", ""),
                    source_type="llm_generated"
                )
                q_id = db.insert_question(new_q)

            r["question_id"] = q_id

        db_responses.append({
            "question_id": q_id,
            "topic_id": t_id or r.get("topic_id"),
            "selected_answer": r["selected_answer"],
            "is_correct": 1 if r["is_correct"] else 0,
            "response_time_seconds": round(elapsed_seconds / len(raw_questions), 1)
        })

    # Save to SQLite
    session_id = db.save_quiz_result(
        student_id=payload.student_id,
        subject_id=session_data["subject_id"],
        score=results["score"],
        total_questions=results["total_questions"],
        responses=db_responses,
        mode=session_data["mode"]
    )

    results["session_id"] = session_id
    results["subject_id"] = session_data["subject_id"]
    results["subject_name"] = session_data["subject_name"]
    results["mode"] = session_data["mode"]

    return results


@router.get("/history/{student_id}")
def get_quiz_history(student_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    history = db.get_student_quiz_history(student_id)
    return history


@router.get("/session/{session_id}")
def get_session_details(session_id: int, student_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    details = db.get_quiz_session_details(session_id, student_id=student_id)
    if not details:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    return details
