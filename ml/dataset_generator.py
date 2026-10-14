"""
Sequential Interaction Dataset Generator for StudyMind.
Generates an academically documented, Item Response Theory (IRT) backed synthetic
student interaction log for benchmarking Classical Baselines and Deep Knowledge Tracing (DKT).
"""

import os
import numpy as np
import pandas as pd
from typing import Tuple


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))


def generate_synthetic_dataset(
    num_students: int = 300,
    min_interactions: int = 40,
    max_interactions: int = 80,
    num_skills: int = 15,
    random_seed: int = 42,
    output_path: str = "data/sample_data.csv"
) -> pd.DataFrame:
    """
    Generates a realistic student interaction dataset using an evolving Item Response Theory model.
    Each student has latent proficiencies per skill that incrementally improve with practice.
    """
    np.random.seed(random_seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    records = []
    
    # Skill names for realism
    skill_names = [
        "Supervised Learning", "Deep Learning", "Evaluation Metrics", "Regularization",
        "Data Structures", "OOP", "Generators", "Concurrency",
        "Probability", "Hypothesis Testing", "Feature Engineering",
        "Big O Complexity", "Trees & BST", "Graphs & Traversal", "Dynamic Programming"
    ]
    assert len(skill_names) == num_skills

    diff_levels = ["Easy", "Medium", "Hard"]
    diff_offsets = {"Easy": -0.7, "Medium": 0.0, "Hard": 0.7}

    for student_id in range(1, num_students + 1):
        # Base student aptitude
        student_base_aptitude = np.random.normal(0.0, 0.8)
        # Latent proficiency vector per skill
        student_proficiencies = student_base_aptitude + np.random.normal(0.0, 0.5, size=num_skills)
        
        # Number of interactions for this student
        n_steps = np.random.randint(min_interactions, max_interactions + 1)
        
        # Skill practice history for this student
        skill_counts = np.zeros(num_skills)

        for step in range(n_steps):
            # Probability of choosing skill: realistic student behavior (some focus on weak skills, some random)
            if np.random.rand() < 0.4:
                # Targeted practice on lower proficiency skill
                probs = np.exp(-student_proficiencies)
                probs /= probs.sum()
                skill_id = int(np.random.choice(num_skills, p=probs))
            else:
                skill_id = int(np.random.randint(0, num_skills))

            skill_counts[skill_id] += 1
            
            diff_label = np.random.choice(diff_levels, p=[0.35, 0.45, 0.20])
            diff_offset = diff_offsets[diff_label]

            # 3PL IRT probability: c + (1 - c) * sigmoid(proficiency - difficulty)
            guess_rate = 0.15
            slip_rate = 0.05
            latent_ability = student_proficiencies[skill_id]
            core_prob = sigmoid(latent_ability - diff_offset)
            prob_correct = guess_rate + (1.0 - guess_rate - slip_rate) * core_prob

            is_correct = 1 if np.random.rand() < prob_correct else 0
            
            # Response time simulation: log-normal distribution conditioned on difficulty and correctness
            base_time = 35.0 + 15.0 * (1 if diff_label == "Hard" else 0)
            resp_time = round(float(np.random.lognormal(np.log(base_time), 0.3)), 1)

            records.append({
                "student_id": student_id,
                "step_index": step,
                "skill_id": skill_id,
                "skill_name": skill_names[skill_id],
                "difficulty": diff_label,
                "difficulty_num": 1 if diff_label == "Easy" else (2 if diff_label == "Medium" else 3),
                "is_correct": is_correct,
                "true_prob": round(float(prob_correct), 4),
                "response_time_seconds": resp_time,
                "timestamp_sec": step * 120 + int(np.random.randint(10, 60))
            })

            # Incremental learning effect: each attempt increases latent proficiency slightly
            # Correct attempt offers reinforcement; incorrect attempt offers learning signal
            learn_delta = 0.08 if is_correct else 0.04
            student_proficiencies[skill_id] = min(3.0, student_proficiencies[skill_id] + learn_delta)

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    return df


def create_data_documentation(output_dir: str = "data") -> None:
    """Generates README.md documenting dataset schema, methodology, and limitations."""
    doc = """# StudyMind Benchmark Dataset Documentation

## Overview
This dataset contains sequential student learning interactions designed for benchmarking Knowledge Tracing algorithms (Classical Logistic Regression / Random Forest vs. Deep Knowledge Tracing GRU).

## Dataset Specifications
- **Format:** CSV (`sample_data.csv`)
- **Number of Students:** 300 unique learners
- **Total Interactions:** ~18,000 sequential attempts
- **Number of Core Skills / Topics:** 15 distinct academic concepts
- **Interactions per Student:** 40 to 80 chronologically ordered steps

## Feature Dictionary
| Column | Type | Description |
|---|---|---|
| `student_id` | Integer | Unique identifier for each student (used for leakage-safe splitting) |
| `step_index` | Integer | Chronological step order for the student (0 to T-1) |
| `skill_id` | Integer | Encoded skill index [0 to 14] |
| `skill_name` | String | Academic skill name |
| `difficulty` | String | Categorical difficulty level ('Easy', 'Medium', 'Hard') |
| `difficulty_num`| Integer | Numeric difficulty score (1=Easy, 2=Medium, 3=Hard) |
| `is_correct` | Binary (0/1) | Target label: whether the student answered correctly |
| `response_time_seconds` | Float | Time in seconds spent on the interaction |
| `timestamp_sec` | Integer | Relative elapsed time in seconds |

## Generation Methodology & Honesty Statement
1. **Underlying Dynamics:** Generated via an evolving Item Response Theory (IRT) process with learning dynamics. Student proficiencies grow incrementally upon exposure to questions, reflecting realistic learning curves.
2. **Academic Honesty:** This dataset is a calibrated synthetic benchmark generated to evaluate the knowledge tracing pipeline. It is not collected from human subjects in a live clinical education study. Real-world deployment should train on verified production telemetry.
3. **Data Leakage Safeguards:** Train/validation/test partitions must strictly split by `student_id` so that an individual student's trajectory is never distributed across both training and evaluation folds.
"""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(doc)


if __name__ == "__main__":
    df = generate_synthetic_dataset()
    create_data_documentation()
    print(f"Dataset generated with {len(df)} records across {df['student_id'].nunique()} students.")
