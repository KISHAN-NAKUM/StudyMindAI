"""
Tests for StudyMind AdaptiveTopicSelector.
Verifies diagnostic balanced allocation for new students and adaptive prioritization
of weak areas with revision questions for active students.
"""

import pytest
import tempfile
import os
from database.db import DatabaseManager
from database.seed_data import seed_database
from quiz.adaptive_selector import AdaptiveTopicSelector
from quiz.generator import QuizGenerator


@pytest.fixture
def adaptive_fixture():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    seed_database(db_path)
    db = DatabaseManager(db_path)
    selector = AdaptiveTopicSelector(db)
    generator = QuizGenerator(db)
    yield selector, generator, db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_cold_start_balanced_diagnostic(adaptive_fixture):
    selector, generator, db = adaptive_fixture

    # New student with zero interactions
    s_id = db.create_student("newbie", "New Learner", "hash", "salt")
    subjects = db.get_all_subjects()
    subj_id = subjects[0].id

    alloc = selector.get_topic_allocation(student_id=s_id, subject_id=subj_id, target_count=10)

    assert alloc["mode"] == "diagnostic"
    assert sum(alloc["topic_distribution"].values()) == 10
    assert "diagnostic" in alloc["rationale"].lower()

    # Generate quiz using this allocation
    quiz = generator.generate_quiz(subject_id=subj_id, topic_distribution=alloc["topic_distribution"])
    assert len(quiz) == 10


def test_adaptive_focus_on_weak_topics(adaptive_fixture):
    selector, generator, db = adaptive_fixture

    s_id = db.create_student("practicing_student", "Learner", "hash", "salt")
    subjects = db.get_all_subjects()
    subj_id = subjects[0].id
    topics = db.get_topics_by_subject(subj_id)
    assert len(topics) >= 2

    weak_topic = topics[0]
    strong_topic = topics[1]

    # Simulate 8 interactions: weak topic failed 4/4 times; strong topic passed 4/4 times
    weak_resps = [{
        "question_id": 1,
        "topic_id": weak_topic.id,
        "selected_answer": "B",
        "is_correct": 0,
        "response_time_seconds": 20.0
    } for _ in range(4)]

    strong_resps = [{
        "question_id": 2,
        "topic_id": strong_topic.id,
        "selected_answer": "A",
        "is_correct": 1,
        "response_time_seconds": 15.0
    } for _ in range(4)]

    db.save_quiz_result(s_id, subj_id, score=0, total_questions=4, responses=weak_resps)
    db.save_quiz_result(s_id, subj_id, score=4, total_questions=4, responses=strong_resps)

    alloc = selector.get_topic_allocation(student_id=s_id, subject_id=subj_id, target_count=10)

    assert alloc["mode"] == "adaptive"
    dist = alloc["topic_distribution"]
    assert sum(dist.values()) == 10

    # Weak topic must have received more practice questions than strong topic
    assert dist[weak_topic.id] > dist[strong_topic.id]
    assert dist[strong_topic.id] > 0, "Revision questions from other topics must still be retained!"

    # Verify quiz generation yields exactly 10 questions
    quiz = generator.generate_quiz(subject_id=subj_id, topic_distribution=dist)
    assert len(quiz) == 10
