"""
Tests for StudyMind database layer and student data isolation.
Verifies that student A cannot access student B's quizzes or responses.
"""

import pytest
import tempfile
import os
from database.db import DatabaseManager
from database.seed_data import seed_database


@pytest.fixture
def seeded_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    seed_database(db_path)
    db = DatabaseManager(db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_student_data_isolation(seeded_db):
    db = seeded_db

    # Create Student A and Student B
    s_a_id = db.create_student("alice", "Alice", "hash_a", "salt_a")
    s_b_id = db.create_student("bob", "Bob", "hash_b", "salt_b")

    subjects = db.get_all_subjects()
    assert len(subjects) > 0
    subj_id = subjects[0].id
    topics = db.get_topics_by_subject(subj_id)
    assert len(topics) > 0
    top_id = topics[0].id

    # Alice takes a quiz
    resp_a = [{
        "question_id": 1,
        "topic_id": top_id,
        "selected_answer": "A",
        "is_correct": 1,
        "response_time_seconds": 12.5
    }]
    session_a_id = db.save_quiz_result(s_a_id, subj_id, score=1, total_questions=1, responses=resp_a)

    # Bob takes a quiz
    resp_b = [{
        "question_id": 1,
        "topic_id": top_id,
        "selected_answer": "B",
        "is_correct": 0,
        "response_time_seconds": 15.0
    }]
    session_b_id = db.save_quiz_result(s_b_id, subj_id, score=0, total_questions=1, responses=resp_b)

    # Verify Alice's history contains ONLY Alice's quiz
    alice_history = db.get_student_quiz_history(s_a_id)
    assert len(alice_history) == 1
    assert alice_history[0]["id"] == session_a_id
    assert alice_history[0]["score"] == 1

    # Verify Bob's history contains ONLY Bob's quiz
    bob_history = db.get_student_quiz_history(s_b_id)
    assert len(bob_history) == 1
    assert bob_history[0]["id"] == session_b_id
    assert bob_history[0]["score"] == 0

    # Cross-access check: Bob CANNOT view Alice's session details
    cross_details = db.get_quiz_session_details(session_a_id, student_id=s_b_id)
    assert cross_details is None, "Security violation: Student B was able to view Student A's quiz session!"

    # Alice CAN view her own session details
    alice_details = db.get_quiz_session_details(session_a_id, student_id=s_a_id)
    assert alice_details is not None
    assert len(alice_details["responses"]) == 1
    assert alice_details["responses"][0]["selected_answer"] == "A"


def test_save_quiz_result_with_none_question_id(seeded_db):
    """Verifies that save_quiz_result gracefully handles None question_id without IntegrityError."""
    db = seeded_db
    student_id = db.create_student("charlie", "Charlie", "hash_c", "salt_c")
    subjects = db.get_all_subjects()
    subj_id = subjects[0].id
    topics = db.get_topics_by_subject(subj_id)
    top_id = topics[0].id

    # Simulated response with None question_id (e.g. from dynamic generator or client)
    resp = [{
        "question_id": None,
        "topic_id": top_id,
        "selected_answer": "C",
        "is_correct": 1,
        "response_time_seconds": 10.0
    }]

    session_id = db.save_quiz_result(student_id, subj_id, score=1, total_questions=1, responses=resp)
    assert session_id is not None

    details = db.get_quiz_session_details(session_id, student_id=student_id)
    assert details is not None
    assert len(details["responses"]) == 1
    assert details["responses"][0]["question_id"] is not None
    assert details["responses"][0]["selected_answer"] == "C"


def test_quiz_generator_assigns_ids_to_all_questions(seeded_db):
    """Verifies that QuizGenerator ensures all questions returned have valid database IDs."""
    from quiz.generator import QuizGenerator
    db = seeded_db
    generator = QuizGenerator(db)
    subjects = db.get_all_subjects()
    subj_id = subjects[0].id

    questions = generator.generate_quiz(subject_id=subj_id, target_count=10)
    assert len(questions) == 10
    for q in questions:
        assert q.get("id") is not None
        assert isinstance(q["id"], int)
        assert q["id"] > 0


def test_get_recent_question_ids(seeded_db):
    """Verifies get_recent_question_ids fetches from recent sessions and respects limit_sessions."""
    db = seeded_db
    s1_id = db.create_student("tester1", "Tester 1", "hash_t1", "salt_t1")
    s2_id = db.create_student("tester2", "Tester 2", "hash_t2", "salt_t2")

    # Initial state: no sessions
    assert db.get_recent_question_ids(s1_id, limit_sessions=3) == []
    assert db.get_recent_question_ids(None) == []

    subjects = db.get_all_subjects()
    subj_id = subjects[0].id
    topics = db.get_topics_by_subject(subj_id)
    top_id = topics[0].id

    # Create 4 sessions for s1 with different questions
    # Session 1 (oldest): question 1
    db.save_quiz_result(s1_id, subj_id, 1, 1, [{"question_id": 1, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}])
    # Session 2: question 2
    db.save_quiz_result(s1_id, subj_id, 1, 1, [{"question_id": 2, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}])
    # Session 3: question 3
    db.save_quiz_result(s1_id, subj_id, 1, 1, [{"question_id": 3, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}])
    # Session 4 (newest): question 4
    db.save_quiz_result(s1_id, subj_id, 1, 1, [{"question_id": 4, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}])

    # Another student s2 session with question 5
    db.save_quiz_result(s2_id, subj_id, 1, 1, [{"question_id": 5, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}])

    # Limit to 3 most recent sessions: should contain 4, 3, 2, but NOT 1 (oldest) and NOT 5 (other student)
    recent = db.get_recent_question_ids(s1_id, limit_sessions=3)
    assert set(recent) == {2, 3, 4}
    assert 1 not in recent
    assert 5 not in recent


def test_avoid_repeated_questions_in_generator(seeded_db):
    """Verifies that QuizGenerator excludes recent questions when unseen ones are available, and reuses when exhausted."""
    from quiz.generator import QuizGenerator
    db = seeded_db
    generator = QuizGenerator(db)

    student_id = db.create_student("repeat_tester", "Repeat Tester", "hash_rt", "salt_rt")
    subjects = db.get_all_subjects()
    subj_id = subjects[0].id
    topics = db.get_topics_by_subject(subj_id)
    top_id = topics[0].id

    all_topic_questions = db.get_questions_for_subject(subj_id, topic_id=top_id)
    assert len(all_topic_questions) >= 2

    # Simulate answering the first question in a quiz session
    first_qid = all_topic_questions[0].id
    db.save_quiz_result(student_id, subj_id, 1, 1, [
        {"question_id": first_qid, "topic_id": top_id, "selected_answer": "A", "is_correct": 1}
    ])

    # If asking for 1 question from this topic with student_id, first_qid should be excluded because unseen exist
    quiz = generator.generate_quiz(subject_id=subj_id, topic_id=top_id, target_count=1, student_id=student_id)
    assert len(quiz) == 1
    assert quiz[0]["id"] != first_qid

    # If target_count requires ALL questions from the topic, it will reuse the seen question without error
    quiz_all = generator.generate_quiz(subject_id=subj_id, topic_id=top_id, target_count=len(all_topic_questions), student_id=student_id)
    quiz_ids = {q["id"] for q in quiz_all}
    assert first_qid in quiz_ids


