"""
Pydantic Schemas for StudyMindAI API.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str


class StudentResponseModel(BaseModel):
    id: int
    username: str
    display_name: str
    created_at: Optional[str] = None


class AuthResult(BaseModel):
    success: bool
    message: str
    student: Optional[StudentResponseModel] = None
    token: Optional[str] = None


# --- Subject & Topic Schemas ---
class TopicModel(BaseModel):
    id: int
    name: str
    subject_id: int
    subject_name: Optional[str] = None


class SubjectModel(BaseModel):
    id: int
    name: str
    description: str
    topics: List[TopicModel] = []


# --- Quiz Schemas ---
class GenerateQuizRequest(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None
    mode: str = "adaptive"  # adaptive, balanced
    difficulty: str = "Medium"
    student_id: Optional[int] = None


class QuizQuestionModel(BaseModel):
    id: Optional[int] = None
    question_id: Optional[int] = None
    subject_id: int
    topic_id: int
    topic: str
    difficulty: str
    question: str
    options: Dict[str, str]
    hint: Optional[str] = ""
    # Note: correct_answer & explanation are hidden during quiz taking


class QuizSessionGenerated(BaseModel):
    subject_id: int
    subject_name: str
    mode: str
    difficulty: str
    rationale: str
    questions: List[QuizQuestionModel]


class SubmitQuizRequest(BaseModel):
    student_id: int
    subject_id: int
    subject_name: str
    mode: str = "adaptive"
    elapsed_seconds: float
    questions: List[Dict[str, Any]]
    answers: Dict[str, str]  # question index (as str or int key) -> selected option 'A'/'B'/'C'/'D'


# --- ML & Simulator Schemas ---
class SimulateStep(BaseModel):
    topic_name: str
    is_correct: bool


class SimulateRequest(BaseModel):
    steps: List[SimulateStep]


class TutorChatRequest(BaseModel):
    message: str
    topic: Optional[str] = None
    subject: Optional[str] = None
    student_id: Optional[int] = None
