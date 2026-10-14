"""
StudyMind: Adaptive Learning Intelligence Platform.
Main Streamlit application implementing student authentication, diagnostic & adaptive
quiz generation, knowledge tracing, feedback analytics, and model evaluation.
"""

import time
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
import pandas as pd

# Load environment variables (.env) if present
load_dotenv()

# Initialize database and seeds before running UI
from database.db import DatabaseManager, DEFAULT_DB_PATH
from database.models import Question
from database.seed_data import seed_database
from auth.service import AuthService
from quiz.generator import QuizGenerator
from quiz.grading import QuizGrader
from quiz.adaptive_selector import AdaptiveTopicSelector
from ml.predict import KnowledgePredictor
from ui.styles import apply_custom_styles
from ui.components import (
    render_hero_header,
    render_kpi_grid,
    build_mastery_radar_chart,
    build_history_timeline_chart,
    build_calibration_plot
)

# Page Configuration
st.set_page_config(
    page_title="StudyMind | Adaptive Learning Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Modern Dark Aesthetic Styles
st.markdown(apply_custom_styles(), unsafe_allow_html=True)


# --- Initialization Helpers ---
@st.cache_resource
def get_services():
    """Initializes and caches backend database, auth, and AI services."""
    seed_database(DEFAULT_DB_PATH)
    db = DatabaseManager(DEFAULT_DB_PATH)
    auth = AuthService(db)
    generator = QuizGenerator(db)
    selector = AdaptiveTopicSelector(db)
    predictor = KnowledgePredictor(db)
    return db, auth, generator, selector, predictor


db, auth_service, quiz_generator, topic_selector, knowledge_predictor = get_services()


# --- Session State Management ---
if "user" not in st.session_state:
    st.session_state.user = None

if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"

if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {
        "active": False,
        "subject_id": None,
        "subject_name": None,
        "questions": [],
        "answers": {},
        "current_idx": 0,
        "start_time": 0.0,
        "mode": "adaptive",
        "rationale": ""
    }

if "last_results" not in st.session_state:
    st.session_state.last_results = None


# --- Authentication View ---
def render_auth_view():
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
        <div class="brand-badge">Machine Learning Prototype</div>
        <h1 style="font-size: 3rem; font-weight: 800; background: linear-gradient(135deg, #818CF8, #C084FC); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            StudyMind
        </h1>
        <p style="color: #94A3B8; font-size: 1.15rem; max-width: 600px; margin: 0 auto;">
            Student-centered adaptive practice platform powered by Deep Knowledge Tracing.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_center, col_r = st.columns([1, 1.4, 1])

    with col_center:
        auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "📝 Create Account"])

        with auth_tab1:
            st.markdown('<div class="study-card">', unsafe_allow_html=True)
            st.subheader("Welcome Back")
            login_user = st.text_input("Username", key="login_username", placeholder="e.g., demo_student")
            login_pass = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("Log In", type="primary", use_container_width=True):
                    ok, msg, student = auth_service.login(login_user, login_pass)
                    if ok and student:
                        st.session_state.user = student
                        st.session_state.nav = "Dashboard"
                        st.rerun()
                    else:
                        st.error(msg)

            with col_btn2:
                if st.button("Use Demo Account", use_container_width=True):
                    ok, msg, student = auth_service.login("demo_student", "password123")
                    if ok and student:
                        st.session_state.user = student
                        st.session_state.nav = "Dashboard"
                        st.rerun()

            st.caption("💡 Quick demo: Click **Use Demo Account** to explore with pre-seeded data.")
            st.markdown('</div>', unsafe_allow_html=True)

        with auth_tab2:
            st.markdown('<div class="study-card">', unsafe_allow_html=True)
            st.subheader("Join StudyMind")
            reg_name = st.text_input("Full Name", placeholder="e.g., Ada Lovelace")
            reg_user = st.text_input("Choose Username", placeholder="e.g., adalovelace")
            reg_pass = st.text_input("Password", type="password", placeholder="At least 6 characters")

            if st.button("Register & Get Started", type="primary", use_container_width=True):
                ok, msg, student = auth_service.register(reg_user, reg_name, reg_pass)
                if ok and student:
                    st.success("Account created successfully! Logging you in...")
                    st.session_state.user = student
                    st.session_state.nav = "Dashboard"
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(msg)
            st.markdown('</div>', unsafe_allow_html=True)


# --- Sidebar Navigation ---
def render_sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 10px 0 20px 0;">
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">
                🧠 StudyMind
            </div>
            <div style="font-size: 0.8rem; color: #94A3B8;">
                Adaptive Student System
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Learner:** `{user.display_name}`")
        
        provider_name = os.getenv("LLM_PROVIDER", "offline").lower()
        if provider_name == "mistral" or os.getenv("MISTRAL_API_KEY"):
            st.markdown("""
            <div style="background: rgba(249, 115, 22, 0.12); border: 1px solid rgba(249, 115, 22, 0.35); border-radius: 8px; padding: 6px 10px; margin-top: 8px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1rem;">⚡</span>
                <div>
                    <div style="font-size: 0.75rem; font-weight: 700; color: #FB923C; letter-spacing: 0.5px;">MISTRAL AI ACTIVE</div>
                    <div style="font-size: 0.70rem; color: #CBD5E1;">Fast Adaptive Practice</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

        nav_options = [
            ("📊 Dashboard", "Dashboard"),
            ("🎯 Take Quiz", "Take Quiz"),
            ("📈 History & Progress", "History")
        ]

        for label, view_key in nav_options:
            is_active = (st.session_state.nav == view_key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{view_key}", use_container_width=True, type=btn_type):
                st.session_state.nav = view_key
        if st.session_state.quiz_state.get("active"):
            st.markdown("---")
            st.warning(f"📝 Test in progress:\n**{st.session_state.quiz_state.get('subject_name', '')}**")
            if st.button("❌ Exit Active Test", key="sidebar_exit_btn", use_container_width=True):
                st.session_state["show_quit_confirm"] = True
                st.session_state.nav = "Take Quiz"
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.quiz_state["active"] = False
            st.session_state.last_results = None
            st.session_state.nav = "Dashboard"
            st.rerun()


# --- View 1: Student Dashboard ---
def render_dashboard_view():
    user = st.session_state.user
    render_hero_header(user.display_name, "Overview")

    # Fetch stats
    history = db.get_student_quiz_history(user.id)
    subjects = db.get_all_subjects()

    total_quizzes = len(history)
    total_questions = sum(h["total_questions"] for h in history)
    avg_score = (sum(h["score"] for h in history) / total_questions * 100) if total_questions > 0 else 0.0

    # Aggregate topics across all subjects
    all_topic_stats = db.get_student_topic_stats(user.id)
    mastered_topics = sum(1 for t in all_topic_stats if t["attempts"] >= 3 and t["accuracy"] >= 75.0)

    render_kpi_grid(total_quizzes, avg_score, total_questions, len([t for t in all_topic_stats if t["attempts"] > 0]))

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.subheader("Curriculum Mastery Breakdown")

        if subjects:
            subj_names = [s.name for s in subjects]
            selected_subj_name = st.selectbox("Filter Subject", subj_names, key="dash_subj_select")
            curr_subj = next(s for s in subjects if s.name == selected_subj_name)
            subject_topics = db.get_student_topic_stats(user.id, curr_subj.id)

            fig_radar = build_mastery_radar_chart(subject_topics)
            st.plotly_chart(fig_radar, use_container_width=True)

            # Honest note
            st.caption(
                "ℹ️ **Mastery Estimation:** Radar values represent empirical and sequential estimates. "
                "Confidence increases as you complete more practice questions."
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.subheader("Score Trajectory")
        fig_timeline = build_history_timeline_chart(history)
        st.plotly_chart(fig_timeline, use_container_width=True)

        st.caption("📈 Green dashed line marks the recommended 70% curriculum proficiency benchmark.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Next Practice Recommendation Banner
    st.markdown('<div class="study-card" style="border-left: 4px solid #6366F1;">', unsafe_allow_html=True)
    st.subheader("🎯 Recommended Next Practice")

    if subjects:
        active_subj = next((s for s in subjects if s.name == selected_subj_name), subjects[0])
        ml_preds = knowledge_predictor.predict_topic_mastery(user.id, active_subj.id)
        alloc = topic_selector.get_topic_allocation(user.id, active_subj.id, ml_predictions=ml_preds)

        st.markdown(f"**Target Subject:** `{active_subj.name}`")
        st.info(f"💡 {alloc['rationale']}")

        col_start, col_custom = st.columns([1, 2])
        with col_start:
            if st.button("🚀 Start 10-Question Adaptive Quiz", type="primary", use_container_width=True):
                start_quiz(active_subj.id, active_subj.name, mode="adaptive", topic_distribution=alloc["topic_distribution"])
    st.markdown('</div>', unsafe_allow_html=True)


# --- View 2: Take Quiz Screen ---
def start_quiz(subject_id: int, subject_name: str, mode: str = "adaptive", 
               topic_id: Optional[int] = None, difficulty: str = "Medium", 
               topic_distribution: Optional[dict] = None):
    """Initializes and loads a 10-question quiz into session state."""
    with st.spinner("Generating 10 questions tailored to your practice goals..."):
        try:
            curr_user = st.session_state.get("user")
            student_id = curr_user.id if curr_user else None
            questions = quiz_generator.generate_quiz(
                subject_id=subject_id,
                topic_id=topic_id,
                difficulty=difficulty,
                topic_distribution=topic_distribution,
                target_count=10,
                student_id=student_id
            )

            st.session_state.quiz_state = {
                "active": True,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "questions": questions,
                "answers": {i: "" for i in range(len(questions))},
                "current_idx": 0,
                "start_time": time.time(),
                "mode": mode,
                "difficulty": difficulty
            }
            st.session_state.nav = "Take Quiz"
            st.rerun()
        except Exception as e:
            st.error(f"Failed to generate quiz: {e}")


def cancel_quiz():
    """Cancels active quiz session without saving results, ensuring student score is not counted."""
    st.session_state.quiz_state = {
        "active": False,
        "subject_id": None,
        "subject_name": None,
        "questions": [],
        "answers": {},
        "current_idx": 0,
        "start_time": 0.0,
        "mode": "adaptive",
        "rationale": ""
    }
    st.session_state["show_quit_confirm"] = False
    st.session_state.nav = "Take Quiz"
    st.toast("Quiz exited. Your progress was discarded and no score was counted.", icon="ℹ️")
    st.rerun()


def render_quiz_view():
    user = st.session_state.user
    state = st.session_state.quiz_state

    # If no quiz is currently active, show Quiz Setup
    if not state.get("active"):
        render_hero_header(user.display_name, "Quiz Setup")
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.subheader("Configure Practice Session")

        subjects = db.get_all_subjects()
        if not subjects:
            st.warning("No subjects found in database.")
            return

        subj_map = {s.name: s for s in subjects}
        selected_subj_name = st.selectbox("Choose Subject", list(subj_map.keys()), key="setup_subj")
        chosen_subject = subj_map[selected_subj_name]

        # Available topics
        topics = db.get_topics_by_subject(chosen_subject.id)
        topic_options = ["All Topics (Adaptive / Balanced)"] + [t.name for t in topics]
        selected_topic_name = st.selectbox("Choose Topic Focus", topic_options, key="setup_topic")

        col1, col2 = st.columns(2)
        with col1:
            quiz_mode = st.radio(
                "Practice Mode",
                ["Adaptive (Prioritizes Topics Needing Practice)", "Balanced Diagnostic (Equal Distribution)"],
                help="Adaptive mode uses your interaction history and ML predictions to balance weak topics and revision."
            )
        with col2:
            quiz_diff = st.selectbox("Difficulty", ["Balanced (Standard)", "Easy", "Medium", "Hard"])

        diff_clean = quiz_diff.split()[0]

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Generate Exactly 10 Questions", type="primary", use_container_width=True):
            topic_id = None
            if selected_topic_name != "All Topics (Adaptive / Balanced)":
                t_match = next((t for t in topics if t.name == selected_topic_name), None)
                if t_match:
                    topic_id = t_match.id

            is_adaptive = "Adaptive" in quiz_mode
            dist = None
            if is_adaptive and topic_id is None:
                ml_preds = knowledge_predictor.predict_topic_mastery(user.id, chosen_subject.id)
                alloc = topic_selector.get_topic_allocation(user.id, chosen_subject.id, ml_predictions=ml_preds)
                dist = alloc["topic_distribution"]

            start_quiz(
                subject_id=chosen_subject.id,
                subject_name=chosen_subject.name,
                mode="adaptive" if is_adaptive else "balanced",
                topic_id=topic_id,
                difficulty=diff_clean,
                topic_distribution=dist
            )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # --- Live Quiz Taker ---
    questions = state["questions"]
    curr_idx = state["current_idx"]
    total_q = len(questions)
    curr_q = questions[curr_idx]

    # Confirmation Prompt if Exit Was Clicked
    if st.session_state.get("show_quit_confirm"):
        st.error(
            "⚠️ **Are you sure you want to exit this test?**\n\n"
            "If you picked this subject by mistake or need to leave, quitting will immediately cancel this session. "
            "**Your score will NOT be counted, and nothing will be saved to your quiz history.**"
        )
        c_confirm, c_cancel, _ = st.columns([1.5, 1.5, 3])
        with c_confirm:
            if st.button("🚨 Yes, Confirm & Exit Test", type="primary", key="btn_confirm_quit_yes", use_container_width=True):
                cancel_quiz()
        with c_cancel:
            if st.button("↩️ No, Keep Taking Test", key="btn_confirm_quit_no", use_container_width=True):
                st.session_state["show_quit_confirm"] = False
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # Header with Progress and Top Exit Button
    col_t1, col_t2, col_t3 = st.columns([2.6, 1.1, 1.1])
    with col_t1:
        st.markdown(f"### 📝 {state['subject_name']} — Question {curr_idx + 1} of {total_q}")
        answered_count = sum(1 for a in state["answers"].values() if a != "")
        st.progress(answered_count / total_q)
    with col_t2:
        st.markdown(f"""
        <div style="text-align: right; padding-top: 10px;">
            <span class="pill-badge pill-indigo">{state['mode'].capitalize()} Mode</span>
            <span class="pill-badge pill-amber">{curr_q.get('difficulty', 'Medium')}</span>
        </div>
        """, unsafe_allow_html=True)
    with col_t3:
        if st.button("❌ Exit Test", key="btn_exit_top", use_container_width=True, help="Exit test without counting your score"):
            st.session_state["show_quit_confirm"] = True
            st.rerun()

    # Question Navigator Pills
    cols_nav = st.columns(total_q)
    for i in range(total_q):
        with cols_nav[i]:
            ans = state["answers"].get(i, "")
            is_answered = bool(ans)
            is_curr = (i == curr_idx)
            btn_label = f"{i+1}{'✓' if is_answered else ''}"
            btn_t = "primary" if is_curr else ("secondary" if not is_answered else "secondary")
            if st.button(btn_label, key=f"q_pill_{i}", use_container_width=True, type=btn_t):
                state["current_idx"] = i
                st.rerun()

    # Question Card
    st.markdown('<div class="question-container">', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 0.85rem; color: #818CF8; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">
        Topic: {curr_q.get('topic', 'General')}
    </div>
    <div class="question-text">
        {curr_q['question']}
    </div>
    """, unsafe_allow_html=True)

    options_dict = curr_q["options"]
    options_keys = ["A", "B", "C", "D"]
    saved_answer = state["answers"].get(curr_idx, "")

    # Format options for radio
    format_func = lambda k: f"({k})  {options_dict.get(k, '')}"

    current_selection_idx = options_keys.index(saved_answer) if saved_answer in options_keys else None

    selected_key = st.radio(
        "Select your answer:",
        options=options_keys,
        index=current_selection_idx,
        format_func=format_func,
        key=f"radio_q_{curr_idx}"
    )

    # Immediately persist choice in session state
    if selected_key:
        state["answers"][curr_idx] = selected_key

    # Collapsible Hint (Does NOT reveal correct answer!)
    if curr_q.get("hint"):
        with st.expander("💡 Need a hint?"):
            st.info(curr_q["hint"])

    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation Controls
    col_prev, col_spacer, col_next, col_submit, col_quit = st.columns([1, 1, 1, 1.3, 1.1])

    with col_prev:
        if curr_idx > 0:
            if st.button("⬅ Previous", use_container_width=True):
                state["current_idx"] -= 1
                st.rerun()

    with col_next:
        if curr_idx < total_q - 1:
            if st.button("Next ➡", type="primary", use_container_width=True):
                state["current_idx"] += 1
                st.rerun()

    with col_submit:
        # Check unanswered
        unanswered = [i + 1 for i in range(total_q) if not state["answers"].get(i)]
        if st.button("Finish & Submit", type="primary", use_container_width=True):
            if unanswered:
                st.warning(f"⚠️ You still have unanswered questions: {unanswered}. Answer all questions or confirm submission.")
            submit_quiz(state, user)

    with col_quit:
        if st.button("❌ Quit Test", key="btn_exit_bottom", use_container_width=True, help="Exit test without counting score"):
            st.session_state["show_quit_confirm"] = True
            st.rerun()


def submit_quiz(state: dict, user):
    """Grades submitted quiz, stores records atomically in SQLite, and displays results."""
    elapsed = time.time() - state["start_time"]
    results = QuizGrader.grade_quiz(state["questions"], state["answers"], elapsed_seconds=elapsed)

    # Prepare atomic database responses
    db_responses = []
    for idx, r in enumerate(results["detailed_reviews"]):
        q_id = r.get("question_id")
        t_id = r.get("topic_id")

        # Fallback if question_id is missing (e.g., dynamically generated or pre-patch session)
        if not q_id:
            matching_q = state["questions"][idx] if idx < len(state["questions"]) else None
            q_text = r.get("question") or (matching_q.get("question") if matching_q else "")

            # Ensure valid topic_id for this subject
            if not t_id or t_id == 0:
                subj_topics = db.get_topics_by_subject(state["subject_id"])
                t_id = subj_topics[0].id if subj_topics else 1

            # Check if question exists in DB
            conn = db.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM questions WHERE subject_id = ? AND question_text = ?",
                (state["subject_id"], q_text)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                q_id = row["id"]
            else:
                opts = r.get("options") or (matching_q.get("options") if matching_q else {})
                new_q = Question(
                    id=None,
                    subject_id=state["subject_id"],
                    topic_id=t_id,
                    difficulty=matching_q.get("difficulty", "Medium") if matching_q else "Medium",
                    question_text=q_text,
                    options=opts,
                    correct_answer=r.get("correct_answer", "A"),
                    explanation=r.get("explanation", ""),
                    hint=r.get("hint", ""),
                    source_type="llm_generated"
                )
                q_id = db.insert_question(new_q)

            r["question_id"] = q_id
            if matching_q:
                matching_q["id"] = q_id

        db_responses.append({
            "question_id": q_id,
            "topic_id": t_id or r.get("topic_id"),
            "selected_answer": r["selected_answer"],
            "is_correct": 1 if r["is_correct"] else 0,
            "response_time_seconds": round(elapsed / len(state["questions"]), 1)
        })

    # Save to SQLite
    session_id = db.save_quiz_result(
        student_id=user.id,
        subject_id=state["subject_id"],
        score=results["score"],
        total_questions=results["total_questions"],
        responses=db_responses,
        mode=state["mode"]
    )

    results["session_id"] = session_id
    results["subject_name"] = state["subject_name"]
    results["subject_id"] = state["subject_id"]

    # Store results & reset active quiz
    st.session_state.last_results = results
    st.session_state.quiz_state["active"] = False
    st.session_state.nav = "Quiz Results"
    st.rerun()


# --- View 3: Results & Feedback Screen ---
def render_results_view():
    results = st.session_state.last_results
    if not results:
        st.info("No recent quiz results to display. Complete a quiz to see results.")
        if st.button("Go to Take Quiz"):
            st.session_state.nav = "Take Quiz"
            st.rerun()
        return

    score = results["score"]
    total = results["total_questions"]
    pct = results["percentage"]
    elapsed = results.get("elapsed_seconds", 0)

    # Celebration Banner
    badge_color = "#10B981" if pct >= 70 else ("#F59E0B" if pct >= 50 else "#F43F5E")
    status_label = "Outstanding Performance! 🌟" if pct >= 80 else ("Good Effort! Keep Practicing 👍" if pct >= 50 else "Focus Area Identified 🎯")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(30, 27, 75, 0.85)); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 16px; padding: 28px; text-align: center; margin-bottom: 24px;">
        <span class="pill-badge pill-indigo">Quiz Session Complete</span>
        <h2 style="font-size: 2.2rem; margin-top: 10px; margin-bottom: 4px; color: #FFFFFF;">
            {status_label}
        </h2>
        <div style="font-size: 3.5rem; font-weight: 800; font-family: 'Outfit', sans-serif; color: {badge_color}; line-height: 1.1;">
            {score} / {total}
        </div>
        <div style="font-size: 1.2rem; color: #CBD5E1; font-weight: 500;">
            {pct}% Score • Completed in {int(elapsed // 60)}m {int(elapsed % 60)}s
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.subheader("Topic Performance Breakdown")

        breakdown_df = pd.DataFrame(results["topic_breakdown"])
        if not breakdown_df.empty:
            breakdown_df = breakdown_df.rename(columns={
                "topic_name": "Topic",
                "attempts": "Questions",
                "correct": "Correct",
                "accuracy": "Accuracy (%)"
            })
            st.dataframe(breakdown_df[["Topic", "Questions", "Correct", "Accuracy (%)"]], use_container_width=True, hide_index=True)

        st.caption(f"ℹ️ {results.get('evaluation_note', '')}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.subheader("🎯 Areas for Improvement")

        weak_topics = results.get("topics_to_practise", [])
        if weak_topics:
            st.write("Based on this quiz session, the following topics are recommended for focused practice:")
            for wt in weak_topics:
                st.markdown(f"""
                <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="font-weight: 600; color: #FDA4AF;">{wt['topic_name']}</div>
                    <div style="font-size: 0.85rem; color: #94A3B8;">Accuracy: {wt['accuracy']}% ({wt['reason']})</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("🎉 Excellent! All tested topics achieved high accuracy in this session.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Practise Recommended Topics Now", type="primary", use_container_width=True):
            user = st.session_state.user
            subj_id = results["subject_id"]
            ml_preds = knowledge_predictor.predict_topic_mastery(user.id, subj_id)
            alloc = topic_selector.get_topic_allocation(user.id, subj_id, ml_predictions=ml_preds)
            start_quiz(subj_id, results["subject_name"], mode="adaptive", topic_distribution=alloc["topic_distribution"])

        st.markdown('</div>', unsafe_allow_html=True)

    # Detailed Question-by-Question Review
    st.markdown('<div class="study-card">', unsafe_allow_html=True)
    st.subheader("Question-by-Question Detailed Review")

    for idx, rev in enumerate(results["detailed_reviews"]):
        card_class = "review-card-correct" if rev["is_correct"] else "review-card-incorrect"
        icon = "✅ Correct" if rev["is_correct"] else "❌ Incorrect"
        icon_color = "#10B981" if rev["is_correct"] else "#F43F5E"

        st.markdown(f"""
        <div class="{card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; color: {icon_color};">{icon}</span>
                <span class="pill-badge pill-indigo">Question {idx + 1} • {rev['topic']}</span>
            </div>
            <div style="font-weight: 600; font-size: 1.05rem; color: #FFFFFF; margin-bottom: 12px;">
                {rev['question']}
            </div>
            <div style="font-size: 0.9rem; margin-bottom: 6px;">
                <strong>Your Answer:</strong> ({rev['selected_answer']}) {rev['selected_text']}
            </div>
            <div style="font-size: 0.9rem; color: #10B981; margin-bottom: 10px;">
                <strong>Correct Answer:</strong> ({rev['correct_answer']}) {rev['correct_text']}
            </div>
            <div style="background: rgba(0, 0, 0, 0.25); border-radius: 8px; padding: 10px 14px; font-size: 0.88rem; color: #CBD5E1; line-height: 1.45;">
                <strong>💡 Explanation:</strong> {rev['explanation']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# --- View 4: History & Progress ---
def render_history_view():
    user = st.session_state.user
    render_hero_header(user.display_name, "Quiz History")

    history = db.get_student_quiz_history(user.id)
    if not history:
        st.markdown('<div class="study-card">', unsafe_allow_html=True)
        st.info("No quizzes completed yet. Complete your first quiz to begin tracking your knowledge growth!")
        if st.button("Start Practice Quiz", type="primary"):
            st.session_state.nav = "Take Quiz"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Table of Past Sessions
    st.markdown('<div class="study-card">', unsafe_allow_html=True)
    st.subheader("Your Practice Sessions")

    hist_df = pd.DataFrame(history)
    hist_df["Date"] = pd.to_datetime(hist_df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    hist_df["Score"] = hist_df.apply(lambda r: f"{r['score']} / {r['total_questions']}", axis=1)
    hist_df["Accuracy"] = hist_df.apply(lambda r: f"{round(r['score'] / r['total_questions'] * 100, 1)}%", axis=1)
    hist_df["Mode"] = hist_df["mode"].str.capitalize()
    hist_df["Subject"] = hist_df["subject_name"]

    st.dataframe(
        hist_df[["id", "Date", "Subject", "Score", "Accuracy", "Mode"]].rename(columns={"id": "Session #"}),
        use_container_width=True,
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Detailed Drill-down
    st.markdown('<div class="study-card">', unsafe_allow_html=True)
    st.subheader("Inspect Past Quiz Responses")
    session_options = {f"Session #{h['id']} — {h['subject_name']} ({h['score']}/{h['total_questions']})": h['id'] for h in history}
    selected_session_label = st.selectbox("Select Session", list(session_options.keys()))
    selected_session_id = session_options[selected_session_label]

    # Data Isolation Check: db method checks student_id = user.id
    details = db.get_quiz_session_details(selected_session_id, student_id=user.id)
    if details:
        st.write(f"**Subject:** {details['subject_name']} | **Date:** {details['created_at']}")
        resps = details.get("responses", [])
        for i, r in enumerate(resps):
            icon = "✅" if r["is_correct"] == 1 else "❌"
            opts = json.loads(r["options_json"]) if isinstance(r["options_json"], str) else r["options_json"]
            st.markdown(f"""
            <div style="border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding: 10px 0;">
                <div style="font-weight: 600;">{i+1}. {r['question_text']} {icon}</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">Topic: {r['topic_name']} | Selected: ({r['selected_answer']}) | Correct: ({r['correct_answer']})</div>
                <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 4px;">{r.get('explanation', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Main Application Router ---
def main():
    if not st.session_state.user:
        render_auth_view()
    else:
        render_sidebar()
        nav = st.session_state.nav

        if nav == "Dashboard":
            render_dashboard_view()
        elif nav == "Take Quiz":
            render_quiz_view()
        elif nav == "Quiz Results":
            render_results_view()
        elif nav == "History":
            render_history_view()


if __name__ == "__main__":
    main()

