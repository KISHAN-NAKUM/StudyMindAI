# StudyMindAI 🧠 — Smart Adaptive Learning Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch-EE4C2C.svg)](https://pytorch.org/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E.svg)](https://scikit-learn.org/)
[![Frontend](https://img.shields.io/badge/Frontend-ES6%20SPA%20%2B%20CSS3-4f46e5.svg)](#frontend-architecture)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

**StudyMindAI** is a modern, student-friendly adaptive learning platform and machine learning showcase. Rather than simply calculating a static quiz score, StudyMindAI models student cognitive mastery over time using **Deep Knowledge Tracing (DKT GRU)** and **Classical ML Baselines**, dynamically generates personalized 10-question practice quizzes to prioritize areas needing improvement, and provides a real-time **conversational AI Study Coach** powered by **WebSockets**.

Designed with a clean **off-white studio aesthetic** (`#f8fafc`), human-centered wording, micro-animations, auditory feedback, and zero external build toolchain requirements (pure native ES6 modules).

---

## 🌟 Key Features

### 1. 📊 Learning Dashboard & Smart Analytics
- **Personalized Learner Overview:** Displays completed practice sessions, average accuracy, current learning streak, and estimated curriculum mastery.
- **Top Recommended Topics:** Highlighting exact topics needing revision with transparent, student-friendly rationales.
- **Interactive Radar Chart & Timeline:** Built using native Canvas-based rendering to visualize skill distribution and historical learning trajectory.

### 2. 🎯 Guaranteed 10-Question Adaptive Practice Engine
- **Diagnostic Mode (Curriculum Survey):** Provides a balanced exploration across foundational topics for new learners or initial diagnostics.
- **Adaptive Practice Mode:** Automatically allocates questions to prioritize weaker topics (~60–70%) while reinforcing previously mastered topics (~30–40%) to prevent regression.
- **Strict Integrity & Verified Question Bank:** Curated questions with unambiguous answer keys, hints, and pedagogical explanations. Correct answers are hidden until submission.

### 3. 🔬 AI Practice Lab & Neural Knowledge Tracing Simulator
- **Live DKT Simulator:** Interactive sandbox showing how a Deep Knowledge Tracing recurrent neural network (GRU) updates its belief of student skill mastery after each answered question.
- **Interactive Timeline:** Step through sequential answers (correct/incorrect) and observe real-time probability shifts across all 15 curriculum topics.
- **Model Benchmark Suite:** Side-by-side performance metrics comparing **Logistic Regression**, **Random Forest**, and **DKT (GRU)** on ROC-AUC, F1-Score, and Expected Calibration Error (ECE).

### 4. 🎓 Real-Time AI Study Coach (WebSocket Streaming)
- **Conversational Intelligence:** Greets learners by name (*"Hey Alex! 👋 How can I help you today?"*) and provides detailed pedagogical explanations, code snippets, and intuitive analogies.
- **Word-by-Word Streaming:** Powered by a bidirectional **WebSocket endpoint (`/api/tutor/ws`)** with a pulsing typing indicator and seamless automatic fallback to HTTP REST (`/api/tutor/chat`).
- **Rich Markdown Formatting:** Automatically renders headings, bold text, bullet points, syntax-highlighted code blocks, and formula explanations.
- **Dual Interface:** Accessible both through the dedicated full-screen coach view and an always-available floating bottom-right drawer.

### 5. 🎨 Design & Aesthetic Excellence
- **Off-White Studio Palette:** Modern, high-contrast, distraction-free color palette (`#f8fafc` canvas, `#ffffff` elevated cards, `#0f172a` typography, `#4f46e5` indigo / `#7c3aed` violet AI accents).
- **Subtle Ambient Canvas:** Lightweight, battery-efficient particle background simulating synaptic neural connections.
- **Web Audio Sound Effects:** Subtle chime on login, clicks on navigation, and success harmonies on quiz submission (with full user mute toggle).

---

## 🏗️ System Architecture

```text
SMA/
├── backend/                        # High-Performance FastAPI Application
│   ├── main.py                     # App factory, static file mounting, CORS, & lifespans
│   ├── schemas.py                  # Pydantic v2 validation models
│   └── routers/
│       ├── auth.py                 # PBKDF2 student auth, registration, & demo login
│       ├── subjects.py             # Curriculum taxonomy, subjects, & topic metadata
│       ├── quiz.py                 # Adaptive quiz generation & grading endpoints
│       ├── analytics.py            # Overview metrics, skill mastery, & score history
│       ├── ml.py                   # Benchmark results & live DKT simulator
│       └── tutor.py                # Conversational AI & WebSocket streaming (/api/tutor/ws)
│
├── frontend/                       # Vanilla ES6 SPA (No Node/NPM dependencies)
│   ├── index.html                  # Single entrypoint HTML5 shell
│   ├── css/
│   │   ├── variables.css           # Design tokens, typography, & off-white studio palette
│   │   └── main.css                # Component styles, animations, & responsive layouts
│   └── js/
│       ├── app.js                  # Core reactive state management & view router
│       ├── api.js                  # Asynchronous REST & WebSocket client (tutorWS)
│       ├── audio.js                # Web Audio API procedural sound synthesis
│       ├── charts.js               # Canvas radar and timeline charting utilities
│       └── particles.js            # Ambient synaptic particle background
│
├── auth/                           # Authentication & Security Layer
│   └── service.py                  # Salted PBKDF2 hashing & verification
│
├── database/                       # Storage & Data Management
│   ├── db.py                       # SQLite connection pool & transaction manager
│   ├── models.py                   # Dataclasses & table schemas
│   └── seed_data.py                # Seeder for subjects, topics, 60+ questions, & demo user
│
├── quiz/                           # Adaptive Assessment Core
│   ├── question_bank.py            # Curated questions across ML, Python, Stats, & Algorithms
│   ├── validator.py                # Pydantic validation for question formatting & keys
│   ├── generator.py                # 10-question adaptive batch generator
│   ├── grading.py                  # Score calculation, review, & constructive feedback
│   └── adaptive_selector.py        # Diagnostic vs Adaptive topic allocation engine
│
├── ml/                             # Machine Learning & Knowledge Tracing
│   ├── dataset_generator.py        # IRT synthetic sequential interaction generator
│   ├── feature_engineering.py      # Causal prior features & student-split partitions
│   ├── train_baseline.py           # Logistic Regression & Random Forest trainer
│   ├── dkt_model.py                # PyTorch GRU recurrent neural network
│   ├── train_dkt.py                # Sequence training loop with padding masks
│   ├── evaluate.py                 # Multi-model evaluation & calibration comparison
│   ├── predict.py                  # Real-time inference engine
│   └── artifacts/                  # Serialized models (.joblib, .pt) & metrics (.json)
│
├── tests/                          # Automated Pytest Suite
│   ├── test_adaptive.py            # Diagnostic & adaptive allocation tests
│   ├── test_auth.py                # Authentication & security tests
│   ├── test_backend.py             # REST endpoints, WebSocket streaming, & greetings
│   ├── test_db.py                  # SQLite database isolation & CRUD tests
│   ├── test_grading.py             # Score grading & feedback tests
│   ├── test_ml.py                  # Data leakage prevention & ML tests
│   └── test_validator.py           # Question validation tests
│
├── run.py                          # Unified single-command launcher
├── requirements.txt                # Python runtime dependencies
└── README.md                       # Platform documentation
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python **3.10+** (tested on Python 3.10, 3.11, 3.12).
- Modern web browser (Chrome, Edge, Firefox, Safari).

### 2. Installation
Clone or navigate to the project directory:
```bash
cd SMA
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Initialize Database (Optional / Pre-seeded)
The database comes pre-seeded with subjects, topics, verified questions, and demo learner **Alex Morgan**. If you ever wish to re-initialize from scratch:
```bash
python -m database.seed_data
```

### 4. Launch the Application
Run the unified launcher:
```bash
python run.py
```

Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

**Interactive OpenAPI Swagger Documentation:**
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 👤 Demo Learner Profile

To immediately explore the platform with historical quiz attempts, mastery metrics, and personalized recommendations, click the **"⚡ Try as Demo Learner"** button on the sign-in screen, or use the credentials:

- **Username:** `demo_student`
- **Password:** `password123`
- **Learner Name:** Alex Morgan

---

## 🔌 API & WebSocket Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status and version info |
| `POST` | `/api/auth/login` | User authentication returning session token |
| `POST` | `/api/auth/demo` | One-click login for demo learner Alex Morgan |
| `POST` | `/api/auth/register` | Register new student profile |
| `GET` | `/api/subjects` | List all available curriculum subjects |
| `POST` | `/api/quiz/generate` | Generate guaranteed 10-question adaptive quiz |
| `POST` | `/api/quiz/submit` | Submit answers, calculate score, update mastery |
| `GET` | `/api/analytics/overview/{id}`| Learner summary metrics and streaks |
| `GET` | `/api/analytics/mastery/{id}` | Radar mastery values across all 15 skills |
| `GET` | `/api/ml/benchmark` | Comparative ML model metrics (DKT vs Baselines)|
| `POST` | `/api/ml/simulate` | Interactive DKT simulator inference |
| `POST` | `/api/tutor/chat` | AI Coach HTTP REST endpoint |
| `WS` | `/api/tutor/ws` | **Real-time AI Coach WebSocket streaming** |

---

## 🔬 Machine Learning Pipeline

StudyMindAI contains a complete, reproducible machine learning pipeline for knowledge tracing:

1. **Synthetic Interaction Generation:**
   ```bash
   python -m ml.dataset_generator
   ```
   Generates synthetic interaction sequences based on Item Response Theory (IRT) across 300 students.

2. **Train Classical ML Baselines (Logistic Regression & Random Forest):**
   ```bash
   python -m ml.train_baseline
   ```
   Extracts strictly causal prior features with leakage-safe student partitioning.

3. **Train Deep Knowledge Tracing (DKT GRU):**
   ```bash
   python -m ml.train_dkt
   ```
   Trains a PyTorch Recurrent Neural Network using padded sequences and masked Cross-Entropy Loss.

4. **Multi-Model Evaluation & Reliability Calibration:**
   ```bash
   python -m ml.evaluate
   ```
   Evaluates all models on a held-out student partition, computing ROC-AUC, F1-Score, and Expected Calibration Error (ECE).

---

## 🧪 Automated Testing

StudyMindAI includes an extensive test suite covering authentication, database isolation, question validation, adaptive allocation, grading, ML leakage prevention, and live WebSocket streaming:

```bash
python -m pytest -v
```

All **33 automated tests** run against isolated test databases and in-memory test clients to ensure zero side-effects.

---

## 🛡️ License & Academic Notice

This project is licensed under the **MIT License**.

> **Note:** StudyMindAI is an adaptive educational technology platform and machine learning showcase. Skill mastery estimations represent statistical approximations of student knowledge state to guide deliberate practice, not definitive measurements of human intellect.
