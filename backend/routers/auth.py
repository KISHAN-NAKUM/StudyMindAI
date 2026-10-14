"""
Authentication endpoints for StudyMindAI.
"""

from fastapi import APIRouter, HTTPException, Depends
from backend.schemas import LoginRequest, RegisterRequest, AuthResult, StudentResponseModel
from auth.service import AuthService
from database.db import DatabaseManager, DEFAULT_DB_PATH

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_auth_service():
    db = DatabaseManager(DEFAULT_DB_PATH)
    return AuthService(db)


@router.post("/login", response_model=AuthResult)
def login(payload: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    ok, msg, student = auth.login(payload.username, payload.password)
    if not ok or not student:
        raise HTTPException(status_code=401, detail=msg)
    return AuthResult(
        success=True,
        message=msg,
        student=StudentResponseModel(
            id=student.id,
            username=student.username,
            display_name=student.display_name,
            created_at=student.created_at
        ),
        token=f"studymind_token_{student.id}"
    )


@router.post("/demo", response_model=AuthResult)
def demo_login(auth: AuthService = Depends(get_auth_service)):
    ok, msg, student = auth.login("demo_student", "password123")
    if not ok or not student:
        raise HTTPException(status_code=401, detail=msg)
    return AuthResult(
        success=True,
        message="Demo login successful",
        student=StudentResponseModel(
            id=student.id,
            username=student.username,
            display_name=student.display_name,
            created_at=student.created_at
        ),
        token=f"studymind_token_{student.id}"
    )


@router.post("/register", response_model=AuthResult)
def register(payload: RegisterRequest, auth: AuthService = Depends(get_auth_service)):
    ok, msg, student = auth.register(payload.username, payload.display_name, payload.password)
    if not ok or not student:
        raise HTTPException(status_code=400, detail=msg)
    return AuthResult(
        success=True,
        message="Registration successful",
        student=StudentResponseModel(
            id=student.id,
            username=student.username,
            display_name=student.display_name,
            created_at=student.created_at
        ),
        token=f"studymind_token_{student.id}"
    )


@router.get("/me/{student_id}", response_model=StudentResponseModel)
def get_current_student(student_id: int):
    db = DatabaseManager(DEFAULT_DB_PATH)
    student = db.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return StudentResponseModel(
        id=student.id,
        username=student.username,
        display_name=student.display_name,
        created_at=student.created_at
    )
