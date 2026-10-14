# StudyMind Benchmark Dataset Documentation

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
