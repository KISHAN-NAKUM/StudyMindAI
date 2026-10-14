"""
Question validator for StudyMind.
Ensures rigorous verification of questions before presentation to students.
"""

from typing import Dict, Any, Tuple, List, Optional
import json


class QuestionValidationError(Exception):
    """Raised when a question fails structural or content validation."""
    pass


class QuestionValidator:
    """Validates question objects from LLM generators or database sources."""

    REQUIRED_KEYS = ["question", "options", "correct_answer", "explanation"]
    VALID_DIFFICULTIES = ["Easy", "Medium", "Hard", "adaptive"]

    @classmethod
    def validate_single_question(cls, q: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates an individual question dictionary.
        Returns: (is_valid: bool, error_message: Optional[str])
        """
        if not isinstance(q, dict):
            return False, "Question must be a dictionary object."

        # Check required fields
        # Note: 'question' or 'question_text'
        text = q.get("question") or q.get("question_text")
        if not text or not isinstance(text, str) or len(text.strip()) < 10:
            return False, "Question text must be at least 10 characters long."

        # Check options
        options = q.get("options")
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except Exception:
                return False, "Options JSON string is malformed."

        if isinstance(options, list):
            if len(options) != 4:
                return False, f"Question must have exactly 4 options; found {len(options)}."
            options_dict = {"A": str(options[0]), "B": str(options[1]), "C": str(options[2]), "D": str(options[3])}
        elif isinstance(options, dict):
            if set(options.keys()) != {"A", "B", "C", "D"}:
                return False, "Options dictionary must contain exactly keys 'A', 'B', 'C', and 'D'."
            options_dict = {k: str(v) for k, v in options.items()}
        else:
            return False, "Options must be a list of 4 items or a dictionary with keys A, B, C, D."

        # Check for empty or duplicate options
        option_values = [v.strip().lower() for v in options_dict.values()]
        if any(len(v) == 0 for v in option_values):
            return False, "One or more options are blank."
        if len(set(option_values)) != 4:
            return False, "Options must be distinct; duplicate options found."

        # Check correct answer
        raw_correct = q.get("correct_answer")
        if not raw_correct:
            return False, "Question is missing 'correct_answer'."

        raw_correct_str = str(raw_correct).strip()
        matched_key = None

        if raw_correct_str.upper() in ["A", "B", "C", "D"]:
            matched_key = raw_correct_str.upper()
        else:
            # Check if answer matches option text
            for key, val in options_dict.items():
                if val.strip().lower() == raw_correct_str.lower():
                    matched_key = key
                    break

        if not matched_key:
            return False, f"Correct answer '{raw_correct}' does not match any of options {options_dict}."

        # Check explanation
        explanation = q.get("explanation")
        if not explanation or not isinstance(explanation, str) or len(explanation.strip()) < 5:
            return False, "Explanation must be provided and at least 5 characters long."

        return True, None

    @classmethod
    def sanitize_and_standardize(cls, q: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes question format into canonical structure."""
        is_valid, err = cls.validate_single_question(q)
        if not is_valid:
            raise QuestionValidationError(f"Invalid question structure: {err}")

        text = (q.get("question") or q.get("question_text", "")).strip()
        options = q.get("options")
        if isinstance(options, str):
            options = json.loads(options)
        if isinstance(options, list):
            options_dict = {"A": str(options[0]).strip(), "B": str(options[1]).strip(), 
                            "C": str(options[2]).strip(), "D": str(options[3]).strip()}
        else:
            options_dict = {k.upper(): str(v).strip() for k, v in options.items()}

        raw_correct = str(q.get("correct_answer")).strip()
        if raw_correct.upper() in ["A", "B", "C", "D"]:
            correct_key = raw_correct.upper()
        else:
            correct_key = "A"
            for k, v in options_dict.items():
                if v.lower() == raw_correct.lower():
                    correct_key = k
                    break

        return {
            "id": q.get("id"),
            "subject_id": q.get("subject_id"),
            "topic_id": q.get("topic_id"),
            "subject": q.get("subject", ""),
            "topic": q.get("topic", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "question": text,
            "options": options_dict,
            "correct_answer": correct_key,
            "explanation": str(q.get("explanation", "")).strip(),
            "hint": str(q.get("hint", "")).strip(),
            "source_type": q.get("source_type", "verified_bank")
        }

    @classmethod
    def validate_quiz_batch(cls, questions: List[Dict[str, Any]], expected_count: int = 10) -> Tuple[bool, Optional[str]]:
        """Validates that a batch of questions contains exactly expected_count non-duplicate questions."""
        if len(questions) != expected_count:
            return False, f"Expected exactly {expected_count} questions, but got {len(questions)}."

        seen_texts = set()
        for i, q in enumerate(questions):
            is_valid, err = cls.validate_single_question(q)
            if not is_valid:
                return False, f"Question {i+1} failed validation: {err}"
            q_text = (q.get("question") or q.get("question_text", "")).strip().lower()
            if q_text in seen_texts:
                return False, f"Duplicate question detected: '{q_text[:40]}...'"
            seen_texts.add(q_text)

        return True, None
