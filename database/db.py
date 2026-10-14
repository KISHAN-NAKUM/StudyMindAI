"""
Database connection and repository operations for StudyMind.
Uses SQLite with foreign keys and thread safety.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from database.models import Student, Subject, Topic, Question, QuizSession, StudentResponse

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "studymind.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a database connection with row factory enabled and performance pragmas."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Performance pragmas for fast concurrent reads and responsive writes
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -32000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        UNIQUE (subject_id, name)
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        difficulty TEXT NOT NULL,
        question_text TEXT NOT NULL,
        options_json TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        hint TEXT,
        source_type TEXT NOT NULL DEFAULT 'verified_bank',
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quiz_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        mode TEXT DEFAULT 'adaptive',
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_session_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        selected_answer TEXT NOT NULL,
        is_correct INTEGER NOT NULL,
        response_time_seconds REAL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (quiz_session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    -- Performance indexes
    CREATE INDEX IF NOT EXISTS idx_questions_sub_top ON questions(subject_id, topic_id);
    CREATE INDEX IF NOT EXISTS idx_quiz_sessions_student ON quiz_sessions(student_id);
    CREATE INDEX IF NOT EXISTS idx_responses_student ON responses(student_id);
    CREATE INDEX IF NOT EXISTS idx_responses_student_topic ON responses(student_id, topic_id);
    CREATE INDEX IF NOT EXISTS idx_responses_session ON responses(quiz_session_id);
    """)

    conn.commit()
    conn.close()


class DatabaseManager:
    """Encapsulates data operations with guaranteed student-level data isolation."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def get_conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    # --- Student Operations ---
    def create_student(self, username: str, display_name: str, password_hash: str, salt: str) -> Optional[int]:
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO students (username, display_name, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
                (username.strip().lower(), display_name.strip(), password_hash, salt, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_student_by_username(self, username: str) -> Optional[Student]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE username = ?", (username.strip().lower(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Student(
                id=row['id'],
                username=row['username'],
                display_name=row['display_name'],
                password_hash=row['password_hash'],
                salt=row['salt'],
                created_at=row['created_at']
            )
        return None

    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Student(
                id=row['id'],
                username=row['username'],
                display_name=row['display_name'],
                password_hash=row['password_hash'],
                salt=row['salt'],
                created_at=row['created_at']
            )
        return None

    # --- Subject & Topic Operations ---
    def get_all_subjects(self) -> List[Subject]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [Subject(id=r['id'], name=r['name'], description=r['description']) for r in rows]

    def get_subject_by_name(self, name: str) -> Optional[Subject]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Subject(id=row['id'], name=row['name'], description=row['description'])
        return None

    def get_topics_by_subject(self, subject_id: int) -> List[Topic]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE subject_id = ? ORDER BY name ASC", (subject_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Topic(id=r['id'], subject_id=r['subject_id'], name=r['name'], description=r['description']) for r in rows]

    def get_topic_by_id(self, topic_id: int) -> Optional[Topic]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Topic(id=row['id'], subject_id=row['subject_id'], name=row['name'], description=row['description'])
        return None

    # --- Question Operations ---
    def get_questions_for_subject(self, subject_id: int, topic_id: Optional[int] = None) -> List[Question]:
        conn = self.get_conn()
        cursor = conn.cursor()
        if topic_id:
            cursor.execute("SELECT * FROM questions WHERE subject_id = ? AND topic_id = ?", (subject_id, topic_id))
        else:
            cursor.execute("SELECT * FROM questions WHERE subject_id = ?", (subject_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Question.from_row(dict(r)) for r in rows]

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Question.from_row(dict(row))
        return None

    def insert_question(self, question: Question) -> int:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO questions (subject_id, topic_id, difficulty, question_text, 
               options_json, correct_answer, explanation, hint, source_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                question.subject_id,
                question.topic_id,
                question.difficulty,
                question.question_text,
                question.options_json() if isinstance(question.options, dict) else json.dumps(question.options),
                question.correct_answer,
                question.explanation,
                question.hint,
                question.source_type
            )
        )
        conn.commit()
        qid = cursor.lastrowid
        conn.close()
        return qid

    # --- Quiz Session & Response Operations ---
    def save_quiz_result(self, student_id: int, subject_id: int, score: int, total_questions: int, 
                         responses: List[Dict[str, Any]], mode: str = "adaptive") -> int:
        """Atomically saves a completed quiz session and individual question responses."""
        conn = self.get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute(
            """INSERT INTO quiz_sessions (student_id, subject_id, created_at, score, total_questions, mode)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student_id, subject_id, now, score, total_questions, mode)
        )
        session_id = cursor.lastrowid

        for resp in responses:
            q_id = resp.get('question_id')
            top_id = resp.get('topic_id')

            # Ensure valid question_id exists in questions table
            if not q_id:
                cursor.execute(
                    "SELECT id FROM questions WHERE subject_id = ? ORDER BY id ASC LIMIT 1",
                    (subject_id,)
                )
                fallback_row = cursor.fetchone()
                if fallback_row:
                    q_id = fallback_row['id']
                else:
                    cursor.execute(
                        """INSERT INTO questions (subject_id, topic_id, difficulty, question_text, 
                           options_json, correct_answer, explanation, hint, source_type)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (subject_id, top_id or 1, "Medium", "Quiz Question", 
                         json.dumps({"A": "A", "B": "B", "C": "C", "D": "D"}), "A", "", "", "llm_generated")
                    )
                    q_id = cursor.lastrowid

            # Ensure valid topic_id exists in topics table
            if not top_id or top_id == 0:
                cursor.execute(
                    "SELECT id FROM topics WHERE subject_id = ? ORDER BY id ASC LIMIT 1",
                    (subject_id,)
                )
                top_row = cursor.fetchone()
                top_id = top_row['id'] if top_row else 1

            cursor.execute(
                """INSERT INTO responses (quiz_session_id, student_id, question_id, topic_id, 
                   selected_answer, is_correct, response_time_seconds, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    student_id,
                    q_id,
                    top_id,
                    resp['selected_answer'],
                    1 if resp['is_correct'] else 0,
                    resp.get('response_time_seconds', None),
                    now
                )
            )

        conn.commit()
        conn.close()
        return session_id

    def get_student_quiz_history(self, student_id: int, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetches history strictly for the requested student."""
        conn = self.get_conn()
        cursor = conn.cursor()
        query = """
            SELECT qs.id, qs.subject_id, s.name as subject_name, qs.created_at, 
                   qs.score, qs.total_questions, qs.mode
            FROM quiz_sessions qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.student_id = ?
        """
        params: list = [student_id]
        if subject_id:
            query += " AND qs.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY qs.created_at DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_quiz_session_details(self, session_id: int, student_id: int) -> Optional[Dict[str, Any]]:
        """Ensures that student A cannot view student B's quiz session details."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT qs.*, s.name as subject_name 
               FROM quiz_sessions qs 
               JOIN subjects s ON qs.subject_id = s.id 
               WHERE qs.id = ? AND qs.student_id = ?""",
            (session_id, student_id)
        )
        session_row = cursor.fetchone()
        if not session_row:
            conn.close()
            return None

        cursor.execute(
            """SELECT r.*, q.question_text, q.options_json, q.correct_answer, q.explanation, 
                      q.hint, t.name as topic_name
               FROM responses r
               JOIN questions q ON r.question_id = q.id
               JOIN topics t ON r.topic_id = t.id
               WHERE r.quiz_session_id = ? AND r.student_id = ?
               ORDER BY r.id ASC""",
            (session_id, student_id)
        )
        responses = [dict(r) for r in cursor.fetchall()]
        conn.close()

        res_dict = dict(session_row)
        res_dict['responses'] = responses
        return res_dict

    def get_student_topic_stats(self, student_id: int, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Calculates topic-level attempts and accuracy for a student."""
        conn = self.get_conn()
        cursor = conn.cursor()
        query = """
            SELECT t.id as topic_id, t.name as topic_name, t.subject_id, s.name as subject_name,
                   COUNT(r.id) as attempts,
                   SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END) as correct_count
            FROM topics t
            JOIN subjects s ON t.subject_id = s.id
            LEFT JOIN responses r ON t.id = r.topic_id AND r.student_id = ?
        """
        params: list = [student_id]
        if subject_id:
            query += " WHERE t.subject_id = ?"
            params.append(subject_id)
        query += " GROUP BY t.id, t.name, t.subject_id, s.name ORDER BY t.name ASC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        stats = []
        for r in rows:
            attempts = r['attempts'] or 0
            correct = r['correct_count'] or 0
            acc = round((correct / attempts) * 100, 1) if attempts > 0 else 0.0
            stats.append({
                'topic_id': r['topic_id'],
                'topic_name': r['topic_name'],
                'subject_id': r['subject_id'],
                'subject_name': r['subject_name'],
                'attempts': attempts,
                'correct_count': correct,
                'accuracy': acc
            })
        return stats

    def get_student_chronological_interactions(self, student_id: int) -> List[Dict[str, Any]]:
        """Returns chronological list of interaction records for a student."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT r.id, r.quiz_session_id, r.question_id, r.topic_id, r.is_correct, 
                      r.created_at, q.difficulty, t.name as topic_name, s.name as subject_name
               FROM responses r
               JOIN questions q ON r.question_id = q.id
               JOIN topics t ON r.topic_id = t.id
               JOIN subjects s ON q.subject_id = s.id
               WHERE r.student_id = ?
               ORDER BY r.created_at ASC, r.id ASC""",
            (student_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_recent_question_ids(self, student_id: int, limit_sessions: int = 3) -> List[int]:
        """Fetches question IDs answered by the student in their most recent quiz sessions."""
        if not student_id or limit_sessions <= 0:
            return []
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT question_id
               FROM responses
               WHERE student_id = ?
                 AND quiz_session_id IN (
                     SELECT id FROM quiz_sessions
                     WHERE student_id = ?
                     ORDER BY created_at DESC, id DESC
                     LIMIT ?
                 )""",
            (student_id, student_id, limit_sessions)
        )
        rows = cursor.fetchall()
        conn.close()
        return [row["question_id"] for row in rows]

