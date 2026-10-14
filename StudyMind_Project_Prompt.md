# StudyMind --- Project Build Prompt

## Role

Act as a senior machine-learning engineer, Python developer, and UI/UX
designer. Help build **StudyMind**, a student-focused adaptive learning
web application for a machine-learning course project. Produce a
working, understandable academic prototype with clean code, clear setup
instructions, and an honest evaluation of the ML components.

## 1. Project goal

StudyMind should do more than show a quiz score. It should track a
student's performance by subject and topic, estimate which topics need
more practice, and adapt future quizzes accordingly.

The basic student workflow is: 1. A student registers or logs in. 2. The
student selects a subject and, where available, a topic or chapter. 3.
The application generates a quiz of **10 questions** appropriate to that
subject and the student's current learning history. 4. The student
answers all 10 questions and submits the quiz. 5. The application grades
the answers and shows the score, topic-wise performance, correct
answers, and explanations. 6. The system identifies topics that appear
weak using accumulated topic-level performance and, when trained and
supported by enough data, predictions from the ML model. 7. On the
student's next practice session, the quiz gives extra attention to weak
topics while still including some revision questions from other topics.
8. Each completed quiz is saved to the student's history so that the
next recommendation can use the new evidence.

Do not label a student as permanently "bad" at a topic. Describe results
as **topics to practise** or **estimated areas for improvement**.

## 2. Important ML design decision

Keep the responsibilities of the components separate:

-   **Question generation:** An LLM or a controlled question bank
    creates subject- and topic-relevant questions.
-   **Scoring and topic analysis:** The application grades answers using
    the stored correct answer, calculates topic-wise performance, and
    records the interaction history.
-   **Classical ML baseline:** Train Logistic Regression and/or Random
    Forest on historical interaction features such as attempts, recent
    accuracy, and topic-wise accuracy.
-   **Deep Knowledge Tracing (DKT):** If a suitable sequential dataset
    is available, train a GRU-based model on ordered student
    interactions to predict the probability of answering the next
    question correctly. Each interaction should include a skill/topic
    identifier and correctness (0/1).
-   **Adaptive selection:** Rank topics for practice using low recent
    accuracy and/or the model's skill-conditioned predictions. Explain
    in the UI that these are estimates, not direct measurements of a
    student's mind or knowledge.
-   **LLM tutoring:** Use the selected topic and difficulty to generate
    new practice content, hints, and explanations.

**Do not pretend that a GRU/DKT model is trained or accurate if no
appropriate dataset exists.** If there is no dataset, first implement a
transparent rule-based topic-analysis fallback and a clearly labelled
demo mode. Build the baseline and DKT training pipeline so they can be
trained when suitable data becomes available. Never present
synthetic/demo results as real model evaluation.

## 3. User authentication and student data

Create a login page and a registration page. Include: - Student name
(for registration), email or username, and password. - Password hashing;
never store plaintext passwords. - Input validation and useful error
messages. - A logout action. - A student dashboard that shows only the
logged-in student's own quiz history and progress. - Persistent storage
using a simple database such as SQLite for the prototype. - Keep secrets
and API keys in environment variables; do not hard-code them. - Do not
collect unnecessary personal information.

For a small academic prototype, use a simple, maintainable
authentication implementation. Clearly document any security limitations
before production use.

## 4. Main pages and features

### A. Login / registration

-   Clean, accessible interface with StudyMind branding.
-   Validate fields and show helpful errors.
-   Allow a student to log in, register, and log out.

### B. Student dashboard

Show: - A subject selector. - Total quizzes attempted. - Recent scores
and progress over time. - Topic-wise performance, number of attempts,
and a clearly worded practice recommendation. - A button to start a new
10-question quiz. - A message explaining that recommendations improve as
more responses are recorded.

### C. Quiz setup

-   Let the student select a subject.
-   Offer available chapters/topics if they exist in the dataset or
    question bank.
-   Let the student choose a difficulty, or default to a balanced
    difficulty.
-   Generate exactly 10 questions for a normal quiz session.
-   Every question must have a stable ID, subject, topic/skill,
    difficulty, question text, answer choices (for multiple choice),
    correct answer, and explanation.
-   Prefer four-option multiple-choice questions for a manageable first
    version.
-   Avoid duplicate questions within a quiz.
-   Validate that every generated question has one unambiguous correct
    answer and that the correct answer is not revealed before
    submission.
-   If the generator cannot produce 10 valid questions, show a clear
    error or use verified questions from the question bank; do not
    silently return fewer questions.

### D. Quiz-taking experience

-   Display one question at a time or a clear list of all 10.
-   Show progress (for example, Question 3 of 10).
-   Allow answers to be changed before submission.
-   Prevent accidental duplicate submissions.
-   Require all 10 answers before final submission, or clearly identify
    unanswered questions and ask the student to confirm.
-   Do not reveal correct answers until submission.

### E. Results and feedback

After submission, show: - Score out of 10 and percentage. - Correct
answers and explanations. - Topic-wise correct/attempted counts and
accuracy. - A concise list of topics recommended for further practice. -
A button to practise weak topics next. - A note that a small number of
questions can give an uncertain estimate.

### F. Adaptive next quiz

-   Use prior responses and topic-level history to give more questions
    from topics that need practice.
-   Keep some questions from other topics for revision and to avoid
    overfitting practice to one weak area.
-   Update topic statistics after every quiz.
-   Make the selection logic transparent and reproducible.
-   If there is little or no history, begin with a balanced diagnostic
    quiz and explain that recommendations are preliminary.
-   Never use future answers or test-set information when computing a
    prediction for an earlier interaction.

### G. History and progress

-   Store quiz date, subject, question IDs, topic IDs, submitted
    answers, correctness, and score.
-   Show past quiz results and topic trends.
-   Ensure one student's records cannot be viewed by another student.

## 5. Data model

Design a small, understandable schema. Suggested tables:

-   **students:** id, display_name, email_or_username, password_hash,
    created_at
-   **subjects:** id, name
-   **topics:** id, subject_id, name
-   **questions:** id, subject_id, topic_id, difficulty, question_text,
    options_json, correct_answer, explanation, source_type
-   **quiz_sessions:** id, student_id, subject_id, created_at, score,
    total_questions
-   **responses:** id, quiz_session_id, question_id, topic_id,
    selected_answer, is_correct, response_time_if_available

Use foreign keys and indexes where appropriate. Do not store the
password itself. Keep question-bank records separate from generated
questions and label the source appropriately.

## 6. ML methodology

Follow this order:

1.  **Data inspection:** Document the dataset source, fields, size,
    target label, and limitations. Do not invent a dataset or claim
    results without running experiments.
2.  **Preprocessing:** Handle missing/duplicate records, encode
    topic/skill IDs, sort interactions chronologically, and create valid
    per-student sequences.
3.  **Leakage-safe split:** Split by student ID into train, validation,
    and test sets where feasible. Do not randomly split individual
    interactions in a way that puts the same student's history in both
    train and test.
4.  **Baseline features:** Use only information available before the
    target question, such as historical attempts, historical
    correctness, recent accuracy, and topic-wise accuracy.
5.  **Baseline models:** Train Logistic Regression and/or Random Forest.
6.  **DKT model:** Implement a GRU sequence model that predicts
    correctness at the next valid interaction. Mask padding in the loss
    and evaluation.
7.  **Evaluation:** Report Accuracy, Precision, Recall, F1-score,
    ROC-AUC when applicable, and Log Loss. Explain class imbalance and
    undefined metrics where relevant. Compare the baseline and DKT on
    the same held-out evaluation setup.
8.  **Calibration and limitations:** Since the model outputs
    probabilities, discuss whether those probabilities are reliable. Do
    not treat a predicted probability as a direct measurement of actual
    knowledge.
9.  **Integration:** Convert predictions into topic-level practice
    priorities and pass the selected topic and difficulty to the
    question generator.
10. **Feedback loop:** Add each new submitted response to the
    interaction history and refresh recommendations. Do not claim
    long-term learning improvement unless a suitable study has been
    conducted.

If the available data is too small or does not contain sequential
student-skill interactions, clearly state that DKT evaluation is not yet
supported and demonstrate the fallback approach instead.

## 7. Question-generation prompt requirements

When calling an LLM, provide a structured request containing: -
Subject - Topic/skill - Target difficulty - Learning objective, if
known - Recent mistakes or misconceptions, if known and appropriate -
Required output format

Ask for exactly the requested number of questions and require structured
JSON. For each question return: - `question` - `options` (four
choices) - `correct_answer` (option key or exact option) -
`explanation` - `hint` - `subject` - `topic` - `difficulty` -
`learning_objective` (if available)

Validate the generated output before displaying it. Reject malformed
JSON, missing fields, duplicate questions, multiple correct answers, and
content unrelated to the selected subject/topic. Keep answers hidden
during the quiz. If a trusted question bank is used, cite or label its
source when available. Do not ask the LLM to infer a student's
weaknesses from unstructured guesses; use the recorded response data and
the ML/rule-based analysis.

## 8. Suggested technology stack

Use a simple stack suitable for a student project: - **Language:**
Python - **Data processing:** Pandas, NumPy - **Classical ML:**
Scikit-learn (Logistic Regression, Random Forest) - **Deep learning:**
PyTorch with a GRU for DKT - **UI:** Streamlit (recommended for a fast
academic prototype; Gradio is an alternative) - **Database:** SQLite -
**Question generation:** Hugging Face Transformers or an LLM API,
configured through environment variables - **Development:**
Jupyter/Google Colab for experiments; Git/GitHub for version control

Choose one UI framework and keep the first implementation focused rather
than building both Streamlit and Gradio.

## 9. Suggested project structure

Organize the implementation into clear modules, for example:

``` text
studymind/
├── app.py
├── pages/
│   ├── login.py
│   ├── register.py
│   ├── dashboard.py
│   ├── take_quiz.py
│   ├── results.py
│   └── history.py
├── auth/
│   └── service.py
├── database/
│   ├── db.py
│   └── models.py
├── quiz/
│   ├── generator.py
│   ├── validator.py
│   ├── grading.py
│   └── adaptive_selector.py
├── ml/
│   ├── feature_engineering.py
│   ├── train_baseline.py
│   ├── dkt_model.py
│   ├── train_dkt.py
│   ├── evaluate.py
│   └── predict.py
├── data/
│   ├── README.md
│   └── sample_data.csv
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

Adjust the structure if a simpler arrangement is more suitable, but keep
authentication, database access, question generation, grading, adaptive
selection, and ML code separate.

## 10. UI and usability requirements

-   Use a modern, uncluttered student-friendly design.
-   Make navigation obvious and consistent.
-   Use readable typography, clear spacing, and accessible contrast.
-   Provide loading indicators during question generation.
-   Show friendly empty states when a student has no history.
-   Show recoverable errors if the LLM/API or database is unavailable.
-   Never expose API keys, stack traces, password hashes, or another
    student's information in the interface.

## 11. Testing and acceptance criteria

The project is complete only when the following can be demonstrated:

-   A student can register, log in, and log out.
-   Passwords are hashed and stored safely.
-   A logged-in student can select a subject and start a quiz.
-   A normal quiz contains exactly 10 valid questions.
-   Answers are not revealed before submission.
-   The system grades answers consistently against stored answer keys.
-   Results include overall score and topic-wise performance.
-   Every response is stored against the correct student and quiz.
-   The next quiz prioritizes topics supported by the student's history
    while retaining some broader revision.
-   A student with no history receives a balanced initial quiz.
-   The application works without an LLM API through a clearly labelled
    local question-bank/demo fallback.
-   Baseline and DKT training/evaluation scripts run when an appropriate
    dataset is supplied.
-   Evaluation metrics are reported honestly and reproducibly.
-   Automated tests cover grading, question validation, adaptive topic
    selection, authentication, and student-data separation.
-   The README explains installation, environment setup, running the
    app, dataset format, model training, tests, and known limitations.

## 12. Deliverables

Provide: 1. Working application source code. 2. Database setup and
schema. 3. Question-generation and validation module. 4. Adaptive
practice logic. 5. Baseline ML pipeline and GRU-DKT pipeline, with clear
dataset assumptions. 6. Tests for important behavior. 7.
`requirements.txt` and `.env.example`. 8. A clear README with setup and
demo instructions. 9. A short project report explaining the problem,
architecture, data, methodology, metrics, results (only if actually
measured), limitations, and future improvements.

## 13. Development approach

Build incrementally in this order: 1. Define the data schema and project
structure. 2. Implement registration/login and student-specific storage.
3. Implement a verified question bank and a working 10-question quiz. 4.
Implement grading, topic-level analytics, and quiz history. 5. Implement
adaptive selection using transparent topic statistics. 6. Add LLM
question generation with validation and fallback. 7. Build and evaluate
the classical ML baseline. 8. Add GRU-DKT only when suitable sequential
data is available. 9. Integrate model predictions into topic
recommendations. 10. Add tests, documentation, and a complete end-to-end
demo.

Before coding, briefly state the architecture and assumptions. Then
implement the project in small, testable steps. Do not omit core files,
use fake model metrics, or claim a feature works unless it is
implemented. Explain any unavoidable limitation and provide commands to
run and test the application.

## 14. Academic honesty and scope

This is an academic prototype, not a clinically or scientifically
validated measure of a student's ability. The project should demonstrate
an adaptive learning workflow and a sound ML experiment. Do not claim
that StudyMind improves learning outcomes without evidence from an
appropriate evaluation. Clearly distinguish real dataset results,
simulated examples, and rule-based demo behavior.
