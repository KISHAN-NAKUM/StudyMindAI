"""
Data models and dataclasses for the StudyMind application.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class Student:
    id: Optional[int]
    username: str
    display_name: str
    password_hash: str
    salt: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Subject:
    id: Optional[int]
    name: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Topic:
    id: Optional[int]
    subject_id: int
    name: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Question:
    id: Optional[int]
    subject_id: int
    topic_id: int
    difficulty: str  # 'Easy', 'Medium', 'Hard'
    question_text: str
    options: Dict[str, str]  # {'A': '...', 'B': '...', 'C': '...', 'D': '...'}
    correct_answer: str      # 'A', 'B', 'C', or 'D'
    explanation: str
    hint: str
    source_type: str         # 'verified_bank' or 'llm_generated'

    def options_json(self) -> str:
        return json.dumps(self.options)

    @classmethod
    def from_row(cls, row: dict) -> 'Question':
        options = json.loads(row['options_json']) if isinstance(row['options_json'], str) else row['options_json']
        return cls(
            id=row['id'],
            subject_id=row['subject_id'],
            topic_id=row['topic_id'],
            difficulty=row['difficulty'],
            question_text=row['question_text'],
            options=options,
            correct_answer=row['correct_answer'],
            explanation=row.get('explanation', ''),
            hint=row.get('hint', ''),
            source_type=row.get('source_type', 'verified_bank')
        )


@dataclass
class QuizSession:
    id: Optional[int]
    student_id: int
    subject_id: int
    created_at: str
    score: int
    total_questions: int
    mode: str = 'adaptive'  # 'adaptive', 'balanced', 'diagnostic'


@dataclass
class StudentResponse:
    id: Optional[int]
    quiz_session_id: int
    student_id: int
    question_id: int
    topic_id: int
    selected_answer: str
    is_correct: int  # 0 or 1
    response_time_seconds: Optional[float] = None
    created_at: Optional[str] = None
