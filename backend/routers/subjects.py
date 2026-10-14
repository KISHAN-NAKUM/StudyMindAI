"""
Subjects and Curriculum endpoints for StudyMindAI.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from database.db import DatabaseManager, DEFAULT_DB_PATH
from backend.schemas import SubjectModel, TopicModel

router = APIRouter(prefix="/api/subjects", tags=["Subjects & Curriculum"])


@router.get("", response_model=List[SubjectModel])
def get_all_subjects():
    db = DatabaseManager(DEFAULT_DB_PATH)
    subjects = db.get_all_subjects()
    result = []
    for s in subjects:
        topics = db.get_topics_by_subject(s.id)
        topic_models = [
            TopicModel(id=t.id, name=t.name, subject_id=t.subject_id, subject_name=s.name)
            for t in topics
        ]
        result.append(
            SubjectModel(
                id=s.id,
                name=s.name,
                description=s.description,
                topics=topic_models
            )
        )
    return result


@router.get("/{subject_id}/topics", response_model=List[TopicModel])
def get_topics_for_subject(subject_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    topics = db.get_topics_by_subject(subject_id)
    return [
        TopicModel(id=t.id, name=t.name, subject_id=t.subject_id, subject_name=t.subject_name)
        for t in topics
    ]
