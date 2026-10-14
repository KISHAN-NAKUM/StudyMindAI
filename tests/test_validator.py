"""
Tests for StudyMind QuestionValidator.
Ensures invalid question schemas, non-four option sets, and duplicate questions are rejected.
"""

import pytest
from quiz.validator import QuestionValidator, QuestionValidationError


def test_valid_question_passes():
    valid_q = {
        "question": "What is the primary function of an activation function?",
        "options": {
            "A": "Introduce non-linearity into the network",
            "B": "Normalize feature inputs to zero mean",
            "C": "Prevent database deadlocks",
            "D": "Compress image files"
        },
        "correct_answer": "A",
        "explanation": "Activation functions introduce non-linearities, allowing neural networks to learn non-linear functions."
    }
    is_valid, err = QuestionValidator.validate_single_question(valid_q)
    assert is_valid is True
    assert err is None


def test_reject_missing_fields_or_short_text():
    # Question text too short
    q = {
        "question": "Why?",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_answer": "A",
        "explanation": "Some explanation"
    }
    is_valid, err = QuestionValidator.validate_single_question(q)
    assert is_valid is False
    assert "at least 10 characters" in err


def test_reject_invalid_options_count():
    # Only 3 options
    q = {
        "question": "Which of the following is an ensemble method?",
        "options": ["Random Forest", "Linear Regression", "Logistic Regression"],
        "correct_answer": "A",
        "explanation": "Random Forest is an ensemble method."
    }
    is_valid, err = QuestionValidator.validate_single_question(q)
    assert is_valid is False
    assert "must have exactly 4 options" in err


def test_reject_duplicate_options():
    q = {
        "question": "Which metric evaluates classification performance?",
        "options": {
            "A": "Accuracy",
            "B": "Accuracy",  # duplicate
            "C": "Precision",
            "D": "Recall"
        },
        "correct_answer": "A",
        "explanation": "Accuracy measures proportion of correct predictions."
    }
    is_valid, err = QuestionValidator.validate_single_question(q)
    assert is_valid is False
    assert "duplicate options found" in err.lower()


def test_reject_unmatched_correct_answer():
    q = {
        "question": "What does Gini Impurity measure in Decision Trees?",
        "options": {
            "A": "Variance",
            "B": "Purity of a node split",
            "C": "Network depth",
            "D": "Learning rate"
        },
        "correct_answer": "E",  # Invalid key
        "explanation": "Gini impurity measures probability of incorrect classification."
    }
    is_valid, err = QuestionValidator.validate_single_question(q)
    assert is_valid is False
    assert "does not match any of options" in err


def test_batch_validation_rejects_duplicates():
    base_q = {
        "question": "What is the primary role of L2 regularization in linear models?",
        "options": {
            "A": "Shrinks weights towards zero",
            "B": "Forces weights exactly to zero",
            "C": "Increases model variance",
            "D": "Removes outliers"
        },
        "correct_answer": "A",
        "explanation": "L2 regularization adds squared penalty on weight magnitudes."
    }
    batch = [base_q.copy() for _ in range(10)]
    is_valid, err = QuestionValidator.validate_quiz_batch(batch, expected_count=10)
    assert is_valid is False
    assert "duplicate question detected" in err.lower()


def test_question_bank_counts_and_difficulty_mix():
    """Verifies that each of the 15 topics has at least 8 verified questions and a mix of Easy, Medium, and Hard."""
    from collections import Counter
    from quiz.question_bank import VERIFIED_QUESTIONS
    from ml.skill_map import TOPIC_NAME_TO_SKILL

    assert len(VERIFIED_QUESTIONS) >= 120, f"Expected at least 120 verified questions, got {len(VERIFIED_QUESTIONS)}"

    # Check each question validates
    for q in VERIFIED_QUESTIONS:
        valid, err = QuestionValidator.validate_single_question(q)
        assert valid is True, f"Question validation failed: {err}"
        assert q.get("hint"), "Question must have a non-empty hint"

    # Check count and difficulty mix per topic
    topic_counts = Counter(q["topic"] for q in VERIFIED_QUESTIONS)
    topic_diffs = {}
    for q in VERIFIED_QUESTIONS:
        topic_diffs.setdefault(q["topic"], set()).add(q["difficulty"])

    assert len(topic_counts) == 15, f"Expected 15 topics, found {len(topic_counts)}"

    for topic_name in TOPIC_NAME_TO_SKILL:
        count = topic_counts.get(topic_name, 0)
        assert count >= 8, f"Topic '{topic_name}' has only {count} questions (minimum 8 required)"
        diffs = topic_diffs.get(topic_name, set())
        assert {"Easy", "Medium", "Hard"}.issubset(diffs), (
            f"Topic '{topic_name}' must contain Easy, Medium, and Hard; got {diffs}"
        )

