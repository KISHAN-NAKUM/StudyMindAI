# StudyMind 🧠 — Student-Focused Adaptive Learning Platform

StudyMind is an adaptive learning web application and machine learning prototype. Rather than simply calculating a static quiz score, StudyMind tracks a student's learning trajectory across subjects and topics, estimates areas needing practice using **Deep Knowledge Tracing (DKT)** and **Classical ML Baselines**, and adaptively composes subsequent 10-question practice quizzes to prioritize weak topics while retaining broader curriculum revision.

---

## 🌟 Key Features

1. **Secure Student Authentication & Data Isolation:**
   - Registration, login, and session management with PBKDF2-HMAC-SHA256 password hashing and random salts.
   - Strict student-level data privacy: records, quiz sessions, and learning trajectories are completely isolated in SQLite.
2. **Guaranteed 10-Question Adaptive Quiz Engine:**
   - Every quiz delivers exactly **10 verified questions** with 4 distinct options, unambiguous answer keys, hints, and detailed explanations.
   - Dynamic LLM generation supported via environment variables, paired with a seamless **verified local question bank fallback** for robust offline operation.
   - Question validation rejects malformed JSON, duplicate text, and ambiguous keys.
   - Correct answers are strictly hidden until student submission.
3. **Transparent Adaptive Practice Selection:**
   - **Diagnostic Mode (Cold Start):** For learners with little or no history (< 5 interactions), provides a balanced curriculum survey.
   - **Adaptive Mode:** Prioritizes topics with lower empirical accuracy and model-predicted mastery (~60–70% of questions) while reserving ~30–40% for revision to prevent overfitting practice.
   - Transparent rationale provided in the UI explaining *why* each topic was selected.
4. **Constructive Growth Feedback:**
   - Detailed per-question review with explanations and hints.
   - Clear classification of **topics to practise** (avoiding fixed labels like "bad at math").
   - Honest disclaimers highlighting sample-size uncertainty.
5. **Machine Learning & Deep Knowledge Tracing Pipeline:**
   - **Item Response Theory (IRT) Synthetic Benchmark:** ~18,000 interactions across 300 students with skill mastery transitions.
   - **Leakage-Safe Partitioning:** Train, validation, and test sets are split strictly by `student_id`.
   - **Causal Baseline Features:** Handcrafted prior-only statistics (`prior_total_accuracy`, `recent_5_accuracy`, `prior_skill_accuracy`).
   - **Classical ML Baselines:** Logistic Regression & Random Forest classifiers.
   - **Deep Knowledge Tracing (DKT GRU):** PyTorch Recurrent Neural Network with masked padding loss.
   - **Calibration Evaluation:** Reliability diagrams and Expected Calibration Error (ECE).
   - **Interactive Knowledge Tracing Simulator:** Live interactive simulator in the web UI.

---

## 🏗️ Project Architecture

```text
SMA/
├── app.py                      # Streamlit application with modern dark UI
├── requirements.txt            # Project dependencies
├── .env.example                # Environment variables template
├── README.md                   # Setup guide and documentation
├── REPORT.md                   # Academic research report and evaluation
├── auth/
│   ├── __init__.py
│   └── service.py              # Secure hashing, registration, and login
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite connection and isolated queries
│   ├── models.py               # Dataclasses and entities
│   └── seed_data.py            # Subjects, topics, questions, & demo user seeder
├── quiz/
│   ├── __init__.py
│   ├── question_bank.py        # Curated verified questions across 4 subjects
│   ├── validator.py            # Strict schema and batch validation
│   ├── generator.py            # 10-question generator with verified bank fallback
│   ├── grading.py              # Grading, topic stats, and feedback logic
│   └── adaptive_selector.py    # Priority topic allocation & rationale engine
├── ml/
│   ├── __init__.py
│   ├── dataset_generator.py    # IRT sequential interaction generator
│   ├── feature_engineering.py  # Causal prior feature extraction & student split
│   ├── train_baseline.py       # Logistic Regression & Random Forest pipeline
│   ├── dkt_model.py            # PyTorch GRU Deep Knowledge Tracing model
│   ├── train_dkt.py            # DKT training loop with sequence masking
│   ├── evaluate.py             # Side-by-side benchmark & calibration curves
│   ├── predict.py              # Real-time inference engine from SQLite history
│   └── artifacts/              # Serialized models (.joblib, .pt) & metrics (.json)
├── ui/
│   ├── __init__.py
│   ├── styles.py               # Custom CSS design system (Dark glassmorphism)
│   └── components.py           # Reusable Plotly charts and UI widgets
├── data/
│   ├── README.md               # Dataset documentation and schema
│   └── sample_data.csv         # Benchmark interaction dataset
└── tests/
    ├── __init__.py
    ├── conftest.py             # PyTorch runtime initialization
    ├── test_auth.py            # Authentication & security tests
    ├── test_db.py              # Database isolation & CRUD tests
    ├── test_validator.py       # Question format validation tests
    ├── test_grading.py         # Scoring & topic analytics tests
    ├── test_adaptive.py        # Diagnostic & adaptive allocation tests
    └── test_ml.py              # Data leakage prevention & ML tests
```

---

## ⚡ Quick Start

### 1. Environment Setup
Verify Python 3.10+ is installed:
```bash
python --version
```

Install dependencies:
```bash
pip install -r requirements.txt
```

*(Optional)* Copy `.env.example` to `.env` if using external LLM APIs:
```bash
cp .env.example .env
```
*Note: If no API keys are provided, StudyMind runs seamlessly in verified offline mode.*

### 2. Initialize Database & Seed Content
Seed subjects, topics, verified questions, and the demo student:
```bash
python -m database.seed_data
```

### 3. Run the Streamlit Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

**Demo Credentials:**
- **Username:** `demo_student`
- **Password:** `password123`
*(Or click the "Use Demo Account" quick-fill button on the login screen).*

---

## 🔬 Machine Learning Experiments

StudyMind includes complete, runnable scripts to regenerate data, train models, and evaluate performance:

### 1. Generate Sequential Dataset
```bash
python -m ml.dataset_generator
```
Generates `data/sample_data.csv` containing ~18,000 interactions across 300 students.

### 2. Train Classical ML Baselines
```bash
python -m ml.train_baseline
```
Trains Logistic Regression and Random Forest on leakage-safe student partitions and saves `ml/artifacts/baseline_model.joblib`.

### 3. Train Deep Knowledge Tracing (DKT GRU)
```bash
python -m ml.train_dkt
```
Trains a PyTorch GRU on padded, masked student sequences and saves weights to `ml/artifacts/dkt_model.pt`.

### 4. Side-by-Side Model Evaluation
```bash
python -m ml.evaluate
```
Compares Logistic Regression, Random Forest, and DKT GRU on the identical held-out student test partition:
- **Metrics:** Accuracy, Precision, Recall, F1-Score, ROC-AUC, Log Loss.
- **Calibration:** Expected Calibration Error (ECE) and reliability diagrams.

---

## 🧪 Automated Testing

Run the full automated test suite (26 tests covering auth, database isolation, grading, adaptive selection, question validation, topic-to-skill mapping, question bank coverage, ceiling analysis, and ML pipeline):

```bash
python -m pytest -v
```

All tests execute against temporary isolated databases to ensure zero side effects.

---

## 🛡️ Academic Honesty & Scope

This application is an **academic prototype** built for educational demonstration:
- Knowledge state predictions represent **statistical approximations** and should never be treated as direct measurements of student ability.
- Recommendations are growth-oriented heuristics to guide study time, not diagnostic judgments.
- Real-world deployment requires production telemetry and pedagogical oversight.
