"""
Grading and feedback service for StudyMind.
Computes overall scores, topic-level performance, identifies estimated areas for improvement,
and prepares constructive, growth-oriented student reviews.
"""

from typing import List, Dict, Any


class QuizGrader:
    """Evaluates student quiz submissions and calculates granular topic performance."""

    @staticmethod
    def grade_quiz(
        questions: List[Dict[str, Any]],
        student_answers: Dict[int, str],
        elapsed_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """
        Grades a submitted quiz.
        Args:
            questions: List of question dictionaries.
            student_answers: Map of question index or question ID to selected option ("A", "B", "C", "D").
            elapsed_seconds: Total time spent taking the quiz.
        Returns:
            Dict containing overall score, percentage, topic breakdown, practice recommendations,
            and question-by-question review data.
        """
        total_questions = len(questions)
        correct_count = 0
        detailed_reviews = []
        topic_stats: Dict[str, Dict[str, Any]] = {}

        for i, q in enumerate(questions):
            q_id = q.get("id")
            # Lookup answer by ID or index
            selected = student_answers.get(q_id) or student_answers.get(i) or student_answers.get(str(i)) or ""
            selected_str = str(selected).strip().upper()
            correct_str = str(q.get("correct_answer")).strip().upper()

            is_correct = (selected_str == correct_str) and len(selected_str) > 0
            if is_correct:
                correct_count += 1

            topic_name = q.get("topic") or "General"
            topic_id = q.get("topic_id", 0)

            if topic_name not in topic_stats:
                topic_stats[topic_name] = {
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "attempts": 0,
                    "correct": 0,
                    "accuracy": 0.0
                }

            topic_stats[topic_name]["attempts"] += 1
            if is_correct:
                topic_stats[topic_name]["correct"] += 1

            # Prepare review item
            detailed_reviews.append({
                "question_id": q_id,
                "topic_id": topic_id,
                "topic": topic_name,
                "question": q.get("question"),
                "options": q.get("options", {}),
                "selected_answer": selected_str,
                "selected_text": q.get("options", {}).get(selected_str, "Unanswered"),
                "correct_answer": correct_str,
                "correct_text": q.get("options", {}).get(correct_str, ""),
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "hint": q.get("hint", "")
            })

        # Calculate topic accuracies
        recommended_practice_topics = []
        strong_topics = []

        for t_name, data in topic_stats.items():
            att = data["attempts"]
            corr = data["correct"]
            acc = round((corr / att) * 100, 1) if att > 0 else 0.0
            data["accuracy"] = acc

            # Constructive classification
            if acc < 60.0:
                recommended_practice_topics.append({
                    "topic_id": data["topic_id"],
                    "topic_name": t_name,
                    "accuracy": acc,
                    "attempts": att,
                    "reason": f"{corr}/{att} correct ({acc}%) in this session"
                })
            else:
                strong_topics.append({
                    "topic_id": data["topic_id"],
                    "topic_name": t_name,
                    "accuracy": acc,
                    "attempts": att
                })

        # Sort recommendations by lowest accuracy first
        recommended_practice_topics.sort(key=lambda x: x["accuracy"])

        score_pct = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0.0

        # Honest disclaimer as required by prompt
        note = (
            "Note: Performance estimates from a 10-question session are preliminary indicators "
            "to guide future practice, not direct measurements of student mastery. Recommendations "
            "become more reliable as more practice sessions are recorded."
        )

        return {
            "score": correct_count,
            "total_questions": total_questions,
            "percentage": score_pct,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "topic_breakdown": list(topic_stats.values()),
            "topics_to_practise": recommended_practice_topics,
            "strong_topics": strong_topics,
            "detailed_reviews": detailed_reviews,
            "evaluation_note": note
        }
