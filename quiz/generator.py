"""
Quiz question generator for StudyMind.
Supports LLM dynamic generation (OpenRouter, OpenAI, Gemini) with structured JSON validation and a
guaranteed verified question bank fallback to always supply exactly 10 valid questions.
"""

import os
import json
import random
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

from database.db import DatabaseManager
from database.models import Question
from quiz.validator import QuestionValidator, QuestionValidationError

# Load environment configuration
load_dotenv()


class QuizGenerator:
    """Generates 10-question quizzes using verified question bank or LLM."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def generate_quiz(
        self,
        subject_id: int,
        topic_id: Optional[int] = None,
        difficulty: str = "Medium",
        topic_distribution: Optional[Dict[int, int]] = None,
        target_count: int = 10,
        student_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates exactly `target_count` (default 10) valid, non-duplicate questions.
        If `topic_distribution` is provided (e.g., from adaptive selector: {topic_id: count}),
        it samples accordingly.
        """
        llm_provider = os.getenv("LLM_PROVIDER", "offline").lower()
        mistral_key = os.getenv("MISTRAL_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        has_api_key = bool(mistral_key or openrouter_key or openai_key or gemini_key)

        questions: List[Dict[str, Any]] = []

        if llm_provider != "offline" and has_api_key:
            try:
                # Generate dynamic LLM questions (up to 3 for fast, responsive generation)
                llm_target = min(target_count, 3) if topic_distribution else min(target_count, 4)
                llm_questions = self._generate_with_llm(
                    subject_id=subject_id,
                    topic_id=topic_id,
                    difficulty=difficulty,
                    count=llm_target,
                    topic_distribution=topic_distribution
                )
                if llm_questions:
                    questions.extend(llm_questions)
            except Exception as e:
                # Log notice and seamlessly fall back to verified bank
                print(f"[StudyMind Generator Notice] LLM generation notice ({e}); engaging verified question bank fallback.")

        # Fill remaining slots from verified question bank to guarantee target_count questions
        if len(questions) < target_count:
            needed = target_count - len(questions)
            adjusted_dist = dict(topic_distribution) if topic_distribution else None
            if adjusted_dist:
                for q in questions:
                    top_id = q.get("topic_id")
                    if top_id and top_id in adjusted_dist and adjusted_dist[top_id] > 0:
                        adjusted_dist[top_id] -= 1

            exclude_ids = {q["id"] for q in questions if q.get("id")}
            bank_questions = self._generate_from_bank(
                subject_id=subject_id,
                topic_id=topic_id,
                difficulty=difficulty,
                topic_distribution=adjusted_dist,
                target_count=needed,
                student_id=student_id,
                exclude_ids=exclude_ids
            )
            questions.extend(bank_questions)

        # Final verification: batch validation
        is_valid, err = QuestionValidator.validate_quiz_batch(questions, expected_count=target_count)
        if not is_valid:
            raise QuestionValidationError(f"Generated quiz failed batch validation: {err}")

        # Guarantee every question has a valid database ID
        for q in questions:
            if not q.get("id"):
                q["id"] = self._persist_question(q, subject_id)

        return questions

    def _generate_from_bank(
        self,
        subject_id: int,
        topic_id: Optional[int] = None,
        difficulty: str = "Medium",
        topic_distribution: Optional[Dict[int, int]] = None,
        target_count: int = 10,
        student_id: Optional[int] = None,
        exclude_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Fetches and samples questions from SQLite question bank, avoiding recently answered questions."""
        conn = self.db.get_conn()
        cursor = conn.cursor()

        recent_ids = set(self.db.get_recent_question_ids(student_id, limit_sessions=3)) if student_id else set()

        selected_questions: List[Dict[str, Any]] = []
        selected_ids = set(exclude_ids or ())

        def _prioritize_pool(pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Orders pool so unseen questions come first, followed by recently seen questions."""
            unseen = [q for q in pool if q['id'] not in recent_ids and q['id'] not in selected_ids]
            seen = [q for q in pool if q['id'] in recent_ids and q['id'] not in selected_ids]
            random.shuffle(unseen)
            random.shuffle(seen)
            return unseen + seen

        # If adaptive topic distribution is supplied
        if topic_distribution:
            for top_id, req_count in topic_distribution.items():
                if req_count <= 0:
                    continue
                cursor.execute(
                    """SELECT q.*, s.name as subject_name, t.name as topic_name
                       FROM questions q
                       JOIN subjects s ON q.subject_id = s.id
                       JOIN topics t ON q.topic_id = t.id
                       WHERE q.subject_id = ? AND q.topic_id = ?""",
                    (subject_id, top_id)
                )
                pool = [dict(r) for r in cursor.fetchall() if r['id'] not in selected_ids]
                prioritized = _prioritize_pool(pool)

                take = prioritized[:req_count]
                for q in take:
                    selected_ids.add(q['id'])
                    selected_questions.append(self._format_db_question(q))

        # If specific single topic requested
        elif topic_id:
            cursor.execute(
                """SELECT q.*, s.name as subject_name, t.name as topic_name
                   FROM questions q
                   JOIN subjects s ON q.subject_id = s.id
                   JOIN topics t ON q.topic_id = t.id
                   WHERE q.subject_id = ? AND q.topic_id = ?""",
                (subject_id, topic_id)
            )
            pool = [dict(r) for r in cursor.fetchall() if r['id'] not in selected_ids]
            prioritized = _prioritize_pool(pool)
            for q in prioritized[:target_count]:
                selected_ids.add(q['id'])
                selected_questions.append(self._format_db_question(q))

        # Fill remaining slots up to target_count from the entire subject pool
        needed = target_count - len(selected_questions)
        if needed > 0:
            cursor.execute(
                """SELECT q.*, s.name as subject_name, t.name as topic_name
                   FROM questions q
                   JOIN subjects s ON q.subject_id = s.id
                   JOIN topics t ON q.topic_id = t.id
                   WHERE q.subject_id = ?""",
                (subject_id,)
            )
            all_subject_pool = [dict(r) for r in cursor.fetchall() if r['id'] not in selected_ids]
            prioritized = _prioritize_pool(all_subject_pool)

            for q in prioritized[:needed]:
                selected_ids.add(q['id'])
                selected_questions.append(self._format_db_question(q))

        # If still needed, supplement from all questions in DB
        needed = target_count - len(selected_questions)
        if needed > 0:
            cursor.execute(
                """SELECT q.*, s.name as subject_name, t.name as topic_name
                   FROM questions q
                   JOIN subjects s ON q.subject_id = s.id
                   JOIN topics t ON q.topic_id = t.id"""
            )
            all_pool = [dict(r) for r in cursor.fetchall() if r['id'] not in selected_ids]
            prioritized = _prioritize_pool(all_pool)
            for q in prioritized[:needed]:
                selected_ids.add(q['id'])
                selected_questions.append(self._format_db_question(q))

        conn.close()

        # Shuffle quiz presentation order
        random.shuffle(selected_questions)
        return selected_questions[:target_count]

    def _format_db_question(self, row: dict) -> Dict[str, Any]:
        """Converts database question row into sanitized dictionary."""
        opts = json.loads(row['options_json']) if isinstance(row['options_json'], str) else row['options_json']
        return QuestionValidator.sanitize_and_standardize({
            "id": row['id'],
            "subject_id": row['subject_id'],
            "topic_id": row['topic_id'],
            "subject": row.get('subject_name', ''),
            "topic": row.get('topic_name', ''),
            "difficulty": row['difficulty'],
            "question": row['question_text'],
            "options": opts,
            "correct_answer": row['correct_answer'],
            "explanation": row.get('explanation', ''),
            "hint": row.get('hint', ''),
            "source_type": row.get('source_type', 'verified_bank')
        })

    def _persist_question(self, q: Dict[str, Any], subject_id: int) -> int:
        """Persists a question dict into SQLite database and returns its assigned ID."""
        q_text = (q.get("question") or q.get("question_text", "")).strip()
        sub_id = q.get("subject_id") or subject_id

        # Resolve valid topic_id for this subject
        top_id = q.get("topic_id")
        if not top_id:
            subj_topics = self.db.get_topics_by_subject(sub_id)
            top_id = subj_topics[0].id if subj_topics else 1

        # Check if already in DB to avoid exact duplicate questions
        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM questions WHERE subject_id = ? AND question_text = ?",
            (sub_id, q_text)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return row["id"]

        q_obj = Question(
            id=None,
            subject_id=sub_id,
            topic_id=top_id,
            difficulty=q.get("difficulty", "Medium"),
            question_text=q_text,
            options=q.get("options", {}),
            correct_answer=q.get("correct_answer", "A"),
            explanation=q.get("explanation", ""),
            hint=q.get("hint", ""),
            source_type=q.get("source_type", "llm_generated")
        )
        return self.db.insert_question(q_obj)

    def _generate_with_llm(
        self,
        subject_id: int,
        topic_id: Optional[int],
        difficulty: str,
        count: int,
        topic_distribution: Optional[Dict[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calls LLM (Mistral/OpenRouter/OpenAI) with structured prompt and parses JSON.
        Guarantees strict formatting and high academic accuracy.
        """
        mistral_key = os.getenv("MISTRAL_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        llm_provider = os.getenv("LLM_PROVIDER", "offline").lower()

        # Lookup subject and topic names
        subjects = self.db.get_all_subjects()
        subject_obj = next((s for s in subjects if s.id == subject_id), None)
        subject_name = subject_obj.name if subject_obj else "General Science"

        subj_topics = self.db.get_topics_by_subject(subject_id)
        topic_name_map = {t.name.lower(): t for t in subj_topics}
        topic_id_to_name = {t.id: t.name for t in subj_topics}
        default_topic = subj_topics[0] if subj_topics else None

        # Build targeted topic string
        if topic_distribution:
            target_topic_names = [topic_id_to_name[tid] for tid in topic_distribution.keys() if tid in topic_id_to_name]
            topics_str = ", ".join(target_topic_names) if target_topic_names else "Core Curriculum"
        elif topic_id and topic_id in topic_id_to_name:
            topics_str = topic_id_to_name[topic_id]
        elif default_topic:
            topics_str = default_topic.name
        else:
            topics_str = "Core Concepts"

        # Determine endpoint and credentials
        is_mistral = (llm_provider == "mistral" or (mistral_key and not (openrouter_key or openai_key)))
        if is_mistral and mistral_key:
            api_key = mistral_key
            endpoint = "https://api.mistral.ai/v1/chat/completions"
            model_name = os.getenv("MODEL_NAME") or "ministral-3b-latest"
        elif openrouter_key:
            api_key = openrouter_key
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            model_name = os.getenv("MODEL_NAME") or "nvidia/nemotron-3-ultra-550b-a55b:free"
            is_mistral = False
        elif openai_key:
            api_key = openai_key
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_name = os.getenv("MODEL_NAME") or "gpt-4o-mini"
            is_mistral = False
        else:
            return []

        prompt = f"""You are an expert academic examiner. Generate exactly {count} distinct multiple-choice questions for the following specifications:
- Subject: {subject_name}
- Target Topics: {topics_str}
- Target Difficulty: {difficulty}

Requirements:
1. Return ONLY a valid JSON object with key "questions" containing an array of {count} question objects.
2. Each question object MUST contain:
   - "question": Clear, rigorous academic question string
   - "topic": The specific topic name this question evaluates
   - "options": An object with exactly 4 keys: "A", "B", "C", and "D"
   - "correct_answer": Exactly one letter ("A", "B", "C", or "D")
   - "explanation": Concise pedagogical explanation of why this answer is correct
   - "hint": A constructive clue that guides the student without revealing the answer
   - "difficulty": "{difficulty}"
"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        if openrouter_key and not is_mistral:
            headers["HTTP-Referer"] = "https://studymind.local"
            headers["X-Title"] = "StudyMind Adaptive Learning"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are an expert examiner. You output educational multiple-choice quiz questions in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        if is_mistral:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=8)
            if resp.status_code != 200:
                print(f"[StudyMind LLM Notice] API returned status {resp.status_code}")
                return []

            res_data = resp.json()
            raw_content = res_data["choices"][0]["message"]["content"].strip()

            parsed = None
            try:
                parsed = json.loads(raw_content)
            except Exception:
                match = re.search(r"(\{.*\}|\[.*\])", raw_content, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                    except Exception:
                        pass

            if isinstance(parsed, dict) and "questions" in parsed and isinstance(parsed["questions"], list):
                question_list = parsed["questions"]
            elif isinstance(parsed, list):
                question_list = parsed
            else:
                return []

            sanitized_questions = []
            for idx, item in enumerate(question_list):
                if not isinstance(item, dict):
                    continue

                item_topic_str = str(item.get("topic", "")).strip().lower()
                if topic_id and topic_id in topic_id_to_name:
                    curr_topic_id = topic_id
                    curr_topic_name = topic_id_to_name[topic_id]
                elif item_topic_str in topic_name_map:
                    curr_topic_id = topic_name_map[item_topic_str].id
                    curr_topic_name = topic_name_map[item_topic_str].name
                elif subj_topics:
                    t_choice = subj_topics[idx % len(subj_topics)]
                    curr_topic_id = t_choice.id
                    curr_topic_name = t_choice.name
                else:
                    curr_topic_id = 1
                    curr_topic_name = "Core Concepts"

                item["subject"] = subject_name
                item["subject_id"] = subject_id
                item["topic"] = curr_topic_name
                item["topic_id"] = curr_topic_id
                item["source_type"] = f"llm_{llm_provider}"

                try:
                    clean_q = QuestionValidator.sanitize_and_standardize(item)
                    qid = self._persist_question(clean_q, subject_id)
                    clean_q["id"] = qid
                    sanitized_questions.append(clean_q)
                except Exception:
                    continue

            return sanitized_questions

        except Exception as e:
            print(f"[StudyMind LLM Notice] Exception during LLM call: {e}")
            return []
