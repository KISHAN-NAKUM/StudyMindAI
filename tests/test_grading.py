"""
Tests for StudyMind QuizGrader.
Verifies scoring logic, percentage calculations, topic-wise statistics, and constructive recommendations.
"""

import pytest
from quiz.grading import QuizGrader


@pytest.fixture
def sample_quiz_questions():
    return [
        {
            "id": 101,
            "topic_id": 1,
            "topic": "Supervised Learning",
            "question": "Q1 text",
            "options": {"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            "correct_answer": "A",
            "explanation": "Exp 1"
        },
        {
            "id": 102,
            "topic_id": 1,
            "topic": "Supervised Learning",
            "question": "Q2 text",
            "options": {"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            "correct_answer": "B",
            "explanation": "Exp 2"
        },
        {
            "id": 103,
            "topic_id": 2,
            "topic": "Evaluation Metrics",
            "question": "Q3 text",
            "options": {"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            "correct_answer": "C",
            "explanation": "Exp 3"
        },
        {
            "id": 104,
            "topic_id": 2,
            "topic": "Evaluation Metrics",
            "question": "Q4 text",
            "options": {"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            "correct_answer": "D",
            "explanation": "Exp 4"
        }
    ]


def test_grading_perfect_score(sample_quiz_questions):
    answers = {101: "A", 102: "B", 103: "C", 104: "D"}
    result = QuizGrader.grade_quiz(sample_quiz_questions, answers, elapsed_seconds=45.0)

    assert result["score"] == 4
    assert result["total_questions"] == 4
    assert result["percentage"] == 100.0
    assert len(result["topics_to_practise"]) == 0
    assert len(result["strong_topics"]) == 2


def test_grading_mixed_performance(sample_quiz_questions):
    # Student gets Supervised Learning 100% correct (2/2), but Evaluation Metrics 0% correct (0/2)
    answers = {101: "A", 102: "B", 103: "A", 104: "A"}  # 103 and 104 incorrect
    result = QuizGrader.grade_quiz(sample_quiz_questions, answers, elapsed_seconds=60.0)

    assert result["score"] == 2
    assert result["total_questions"] == 4
    assert result["percentage"] == 50.0

    # Evaluation Metrics should be flagged as an area for improvement (<60%)
    practice_names = [t["topic_name"] for t in result["topics_to_practise"]]
    assert "Evaluation Metrics" in practice_names

    strong_names = [t["topic_name"] for t in result["strong_topics"]]
    assert "Supervised Learning" in strong_names


def test_grading_unanswered_questions(sample_quiz_questions):
    # Student leaves questions empty
    answers = {101: "A"}  # Only 1 answered
    result = QuizGrader.grade_quiz(sample_quiz_questions, answers)

    assert result["score"] == 1
    assert result["total_questions"] == 4
    assert result["percentage"] == 25.0
