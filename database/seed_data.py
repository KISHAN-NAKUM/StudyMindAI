"""
Database Seeder for StudyMind.
Seeds subjects, topics, verified questions, and demo student into the SQLite database.
"""

import hashlib
import os
import json
from database.db import DatabaseManager, DEFAULT_DB_PATH
from quiz.question_bank import VERIFIED_QUESTIONS


def hash_password(password: str, salt: str = "studymind_demo_salt") -> str:
    """Helper to generate pbkdf2 hash for seeding demo user."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


def seed_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Seeds the database with foundational subjects, topics, questions, and a demo student."""
    db = DatabaseManager(db_path)
    conn = db.get_conn()
    cursor = conn.cursor()

    # 1. Seed Subjects & Topics
    subject_topics_map = {
        "Machine Learning": [
            "Supervised Learning",
            "Deep Learning",
            "Evaluation Metrics",
            "Regularization & Generalization"
        ],
        "Python Programming": [
            "Data Structures & Collections",
            "Object-Oriented Programming",
            "Generators & Iterators",
            "Error Handling & Concurrency"
        ],
        "Data Science & Statistics": [
            "Probability & Distributions",
            "Hypothesis Testing",
            "Feature Engineering & Preprocessing"
        ],
        "Algorithms & Data Structures": [
            "Big O Complexity & Asymptotics",
            "Trees & Binary Search Trees",
            "Graphs & Traversal",
            "Dynamic Programming"
        ]
    }

    subject_ids = {}
    topic_ids = {}

    for subj_name, topics in subject_topics_map.items():
        cursor.execute("SELECT id FROM subjects WHERE name = ?", (subj_name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO subjects (name, description) VALUES (?, ?)", 
                           (subj_name, f"Core curriculum for {subj_name}"))
            s_id = cursor.lastrowid
        else:
            s_id = row['id']
        subject_ids[subj_name] = s_id

        for top_name in topics:
            cursor.execute("SELECT id FROM topics WHERE subject_id = ? AND name = ?", (s_id, top_name))
            t_row = cursor.fetchone()
            if not t_row:
                cursor.execute("INSERT INTO topics (subject_id, name, description) VALUES (?, ?, ?)",
                               (s_id, top_name, f"Fundamental concepts in {top_name}"))
                t_id = cursor.lastrowid
            else:
                t_id = t_row['id']
            topic_ids[(subj_name, top_name)] = t_id

    # 2. Seed Questions
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    q_count = cursor.fetchone()['count']
    if q_count == 0:
        for q in VERIFIED_QUESTIONS:
            s_id = subject_ids.get(q['subject'])
            t_id = topic_ids.get((q['subject'], q['topic']))
            if s_id and t_id:
                cursor.execute(
                    """INSERT INTO questions (subject_id, topic_id, difficulty, question_text, 
                       options_json, correct_answer, explanation, hint, source_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s_id,
                        t_id,
                        q['difficulty'],
                        q['question'],
                        json.dumps(q['options']),
                        q['correct_answer'],
                        q['explanation'],
                        q['hint'],
                        'verified_bank'
                    )
                )

    # 3. Seed Demo Student
    cursor.execute("SELECT id FROM students WHERE username = ?", ("demo_student",))
    row = cursor.fetchone()
    if not row:
        salt = os.urandom(16).hex()
        pwd_hash = hash_password("password123", salt)
        cursor.execute(
            """INSERT INTO students (username, display_name, password_hash, salt, created_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            ("demo_student", "Alex Morgan", pwd_hash, salt)
        )
    else:
        cursor.execute("UPDATE students SET display_name = ? WHERE username = ?", ("Alex Morgan", "demo_student"))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully!")
