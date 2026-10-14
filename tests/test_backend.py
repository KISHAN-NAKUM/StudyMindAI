"""
Tests for StudyMindAI FastAPI backend endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["platform"] == "StudyMindAI"


def test_auth_demo_login():
    response = client.post("/api/auth/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["student"]["username"] == "demo_student"
    assert "token" in data


def test_get_subjects():
    response = client.get("/api/subjects")
    assert response.status_code == 200
    subjects = response.json()
    assert len(subjects) >= 4
    subj_names = [s["name"] for s in subjects]
    assert "Machine Learning" in subj_names
    assert "Python Programming" in subj_names


def test_generate_quiz_and_submit():
    # 1. Demo login
    auth_resp = client.post("/api/auth/demo").json()
    student_id = auth_resp["student"]["id"]

    # 2. Get subjects
    subjects = client.get("/api/subjects").json()
    subj_id = subjects[0]["id"]

    # 3. Generate quiz
    gen_resp = client.post("/api/quiz/generate", json={
        "subject_id": subj_id,
        "mode": "diagnostic",
        "difficulty": "Medium",
        "student_id": student_id
    })
    assert gen_resp.status_code == 200
    quiz_data = gen_resp.json()
    assert len(quiz_data["questions"]) == 10
    session_token = quiz_data["session_token"]

    # 4. Submit quiz answers
    answers = {str(i): "A" for i in range(10)}
    sub_resp = client.post("/api/quiz/submit", json={
        "session_token": session_token,
        "student_id": student_id,
        "answers": answers
    })
    assert sub_resp.status_code == 200
    res_data = sub_resp.json()
    assert res_data["total_questions"] == 10
    assert "percentage" in res_data
    assert "topic_breakdown" in res_data


def test_analytics_endpoints():
    auth_resp = client.post("/api/auth/demo").json()
    student_id = auth_resp["student"]["id"]

    # Overview
    ov_resp = client.get(f"/api/analytics/overview/{student_id}")
    assert ov_resp.status_code == 200
    ov_data = ov_resp.json()
    assert "total_quizzes" in ov_data
    assert "avg_accuracy" in ov_data

    # Mastery
    m_resp = client.get(f"/api/analytics/mastery/{student_id}")
    assert m_resp.status_code == 200
    m_data = m_resp.json()
    assert len(m_data) > 0


def test_ml_endpoints():
    # Benchmark
    bench_resp = client.get("/api/ml/benchmark")
    assert bench_resp.status_code == 200
    bench = bench_resp.json()
    assert "models" in bench
    assert "Deep Knowledge Tracing (DKT GRU)" in bench["models"]

    # Simulation
    sim_resp = client.post("/api/ml/simulate", json={
        "steps": [
            {"topic_name": "Supervised Learning", "is_correct": True},
            {"topic_name": "Deep Learning", "is_correct": False}
        ]
    })
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert len(sim_data["skills"]) == 15


def test_tutor_chat():
    resp = client.post("/api/tutor/chat", json={
        "message": "Explain deep learning"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "Deep Learning" in data["reply"]


def test_tutor_greeting_personalized():
    # When user says "hi" with username Alex
    from backend.routers.tutor import generate_tutor_response
    reply = generate_tutor_response("hi", username="Alex")
    assert "Hey Alex!" in reply
    assert "How can I help you today?" in reply

    # When user says "hello!"
    reply2 = generate_tutor_response("hello!", username="Maya")
    assert "Hey Maya!" in reply2
    assert "How can I help you today?" in reply2


def test_tutor_websocket():
    with client.websocket_connect("/api/tutor/ws") as websocket:
        # Send greeting
        websocket.send_json({
            "message": "hi",
            "username": "Alex",
            "student_id": 1
        })

        # Expect start event
        start_msg = websocket.receive_json()
        assert start_msg["type"] == "start"

        # Receive streaming chunks until done
        accumulated = ""
        while True:
            chunk_msg = websocket.receive_json()
            if chunk_msg["type"] == "chunk":
                accumulated += chunk_msg["content"]
            elif chunk_msg["type"] == "done":
                assert "Hey Alex!" in chunk_msg["reply"]
                assert "How can I help you today?" in chunk_msg["reply"]
                break

        # Also send a concept question over the same websocket
        websocket.send_json({
            "message": "Explain L1 vs L2",
            "username": "Alex",
            "student_id": 1
        })
        start_msg2 = websocket.receive_json()
        assert start_msg2["type"] == "start"
        while True:
            chunk_msg2 = websocket.receive_json()
            if chunk_msg2["type"] == "done":
                assert "L1" in chunk_msg2["reply"]
                assert "L2" in chunk_msg2["reply"]
                break
