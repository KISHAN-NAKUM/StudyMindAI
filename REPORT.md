# StudyMind — Academic Project Report

**Project Title:** StudyMind: An Adaptive Learning Prototype with Deep Knowledge Tracing and Transparent Topic Practice  
**Course Context:** Machine Learning & Intelligent Educational Systems  
**Date:** October 2026  

---

## 1. Executive Summary & Problem Formulation

Standard digital educational assessments typically treat evaluation as a static measurement: a student completes a fixed exam, receives a percentage score, and moves forward with minimal actionable feedback. In contrast, modern cognitive science and Intelligent Tutoring Systems (ITS) recognize that student learning is inherently dynamic, continuous, and skill-dependent.

**StudyMind** addresses three fundamental limitations of traditional quiz platforms:
1. **Static vs. Dynamic Understanding:** Traditional scores fail to track skill evolution over time.
2. **Fixed Question Selection:** Standard quizzes administer uniform question sets regardless of past mistakes, leading to either student frustration on neglected weak topics or boredom on already mastered concepts.
3. **Lack of Transparency & Model Calibration:** Educational applications frequently treat machine learning models as black boxes or make unverified claims about predicting student intelligence.

StudyMind formulates adaptive learning as a sequential knowledge tracing problem: given a chronological history of a learner's past responses $H_t = \{(k_1, y_1), (k_2, y_2), \dots, (k_t, y_t)\}$ where $k_i \in \{1, \dots, K\}$ denotes the skill/topic and $y_i \in \{0, 1\}$ denotes correctness, the system models the probability $P(y_{t+1} = 1 \mid k_{t+1}, H_t)$ that the student will answer a future question on skill $k_{t+1}$ correctly. This estimate directly informs subsequent 10-question practice quizzes to prioritize estimated areas for improvement while preserving curriculum revision.

---

## 2. System Architecture & Separation of Concerns

StudyMind enforces strict architectural separation between user interface, storage, question generation, and statistical learning components:

```
[ Student Web Interface (Streamlit) ]
       │                      │
       ▼                      ▼
[ Auth & Data Isolation ]   [ Quiz Engine ]
(PBKDF2 Hashing, SQLite)   (Validation, Grading, Adaptive Selector)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
     [ Verified Question Bank ]   [ Knowledge Predictor ]
     (Offline Curated Prompts)    (Classical Baseline & DKT GRU)
```

1. **User Authentication & Data Privacy:** Passwords hashed with PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte random salt). Database queries strictly filter by `student_id`, ensuring absolute data isolation across learners.
2. **Question Generator & Validator:** Every quiz generates exactly 10 multiple-choice questions. Each question must possess four distinct options, an unambiguous correct answer, and an explanatory justification. If external LLM generation is unavailable, the verified local question bank serves as an automatic, transparent fallback.
3. **Grading & Constructive Feedback:** Evaluates responses against canonical answer keys, calculates topic-wise accuracy, and classifies results into *topics to practise* or *estimated areas for improvement* (avoiding deficit-based labels).
4. **Adaptive Topic Selector:** Allocates question counts for the next quiz based on recent empirical accuracy and model predictions.
5. **Machine Learning Pipeline:** Modular data synthesis, causal feature engineering, baseline training, recurrent neural network training, and calibration evaluation.

---

## 3. Benchmark Dataset & Simulation Dynamics

To rigorously benchmark knowledge tracing without fabricating human study data, StudyMind incorporates a calibrated sequential simulation engine (`ml/dataset_generator.py`) grounded in **Item Response Theory (IRT)** with dynamic cognitive transitions:

- **Cohort Size:** 300 simulated students.
- **Interactions:** 18,258 total chronological interactions (~40 to 80 interactions per student).
- **Core Curriculum:** 15 distinct topics across Machine Learning, Python, Statistics, and Algorithms.
- **Generative Process:**
  - Each learner possesses a base latent aptitude $\theta_s \sim \mathcal{N}(0, 0.8)$ and skill-specific initial proficiencies $\mu_{s, k} \sim \mathcal{N}(\theta_s, 0.5)$.
  - Question difficulty offsets $d_q \in \{-0.7, 0.0, +0.7\}$ for Easy, Medium, and Hard tiers.
  - Interaction outcome determined via a 3-Parameter Logistic (3PL) IRT formulation with guess rate $c = 0.15$ and slip rate $s = 0.05$:
    $$P(y = 1) = c + (1 - c - s) \cdot \sigma(\mu_{s, k} - d_q)$$
  - **Learning Dynamics:** Following each attempt, skill proficiency undergoes incremental reinforcement: $\mu_{s, k} \leftarrow \min(3.0, \mu_{s, k} + \Delta)$ where $\Delta \in \{0.04, 0.08\}$.

---

## 4. Machine Learning Methodology

### 4.1. Leakage-Safe Partitioning
Data leakage is a pervasive flaw in educational data mining, where interaction records from the same student are randomly partitioned across training and testing splits. StudyMind strictly enforces a **student-level split**:
- **Training Cohort:** 210 students (12,693 interactions, 70%)
- **Validation Cohort:** 45 students (2,794 interactions, 15%)
- **Held-Out Test Cohort:** 45 students (2,771 interactions, 15%)

Zero student overlap exists across folds.

### 4.2. Causal Feature Engineering (Baselines)
Features extracted for interaction $t$ rely strictly on events occurring at steps $0 \dots t-1$. No future or target-step information leaks into predictors:
- `prior_total_attempts`: Cumulative questions answered before step $t$.
- `prior_total_accuracy`: Historical accuracy across all past questions.
- `prior_skill_attempts`: Specific attempts on skill $k$ prior to step $t$.
- `prior_skill_accuracy`: Historical accuracy on skill $k$ prior to step $t$.
- `recent_5_accuracy`: Moving average over the last 5 interactions.
- `skill_recent_3_accuracy`: Moving average over the last 3 interactions for skill $k$.
- `difficulty_num`: Numeric difficulty indicator (1, 2, or 3).
- `skill_id`: Categorical topic index.

### 4.3. Deep Knowledge Tracing (DKT GRU)
Following Piech et al. (2015), DKT models student learning as a Recurrent Neural Network:
- **Input Encoding:** Interaction at step $t$ is mapped to token $x_t = 1 + k_t + y_t \cdot K \in [1, 2K]$ (where $0$ is padding index).
- **Embedding & Recurrence:** Token $x_t$ is projected into a 64-dimensional dense embedding space, passed through a Gated Recurrent Unit (hidden dimension 64, dropout 0.2), and projected to $K$ output logits.
- **Sequence Masking & Loss Formulation:** Variable-length student trajectories are padded to batch length. The loss is computed using `BCEWithLogitsLoss` evaluated strictly at valid transition steps for the specific skill attempted at step $t+1$:
  $$\mathcal{L} = \frac{1}{\sum m_{t}} \sum_{t=1}^{T-1} m_t \cdot \ell\left(\hat{y}_{t+1, k_{t+1}}, y_{t+1}\right)$$
  where $m_t \in \{0, 1\}$ is the validity mask.

---

## 5. Experimental Results & Model Comparison

All models were evaluated on the **identical held-out test cohort** of 45 unseen students. Specifically, Deep Knowledge Tracing (DKT) is evaluated on 2,726 transitions (2,771 interactions minus 45 first steps, which have no history), while tabular baselines evaluate all 2,771 interactions (with cold-start neutral priors at step 0):

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Log Loss | Expected Calibration Error (ECE) |
|---|---|---|---|---|---|---|---|
| **Majority-Class / Training-Mean (Trivial Baseline)** | 0.6016 | 0.6016 | **1.0000** | **0.7512** | 0.5000 | 0.6728 | **0.0143** |
| **Logistic Regression (Baseline)** | **0.6250** | 0.6481 | 0.8242 | 0.7256 | **0.6283** | **0.6484** | 0.0147 |
| **Random Forest (Baseline)** | 0.6160 | **0.6495** | 0.7858 | 0.7112 | 0.6137 | 0.6558 | 0.0353 |
| **Deep Knowledge Tracing (GRU)** | 0.5906 | 0.6329 | 0.7610 | 0.6910 | 0.5774 | 0.6753 | 0.0526 |

### 5.1. Critical Discussion of Results
1. **Sample Efficiency & Prior Feature Strength:** Handcrafted summary statistics (`recent_5_accuracy`, `prior_skill_accuracy`) encode strong inductive biases that allow linear models to perform exceptionally well on small-to-medium sequence lengths (~50 steps).
2. **DKT Overfitting Mitigation:** The recurrent GRU architecture contains 27,919 parameters (computed directly from the model: 1,984 embedding weights + 24,960 GRU weights and biases + 975 output projection weights and biases), compared to 9 weights in Logistic Regression. Retraining with early stopping on validation loss (patience 5) and L2 weight decay ($1 \times 10^{-4}$) effectively curbed earlier overconfidence: ROC-AUC improved from 0.5487 to 0.5774, Log Loss dropped to 0.6753, and ECE improved significantly from 0.1215 to 0.0526.
3. **Class Imbalance & Base Rate:** Because students improve over time, positive labels ($y = 1$) constitute approximately 60.2% of test cohort interactions. Models achieve high recall by identifying foundational proficiency trends.

### 5.2. Ceiling Analysis and Trivial Baseline
To benchmark the true informativeness of our models, StudyMind implements both an empirical lower bound and a theoretical Bayes-optimal upper bound:

1. **Trivial Baseline (Majority-Class / Training-Mean):**
   - **Method:** Predicts the constant empirical training accuracy ($\bar{p}_{\text{train}} \approx 0.591$) and the majority class ($y = 1$) for every test query.
   - **Performance:** Accuracy = 0.6016, F1 = 0.7512, ROC-AUC = 0.5000, Log Loss = 0.6728, ECE = 0.0143.
   - **Pedagogical Takeaway:** Accuracy metrics in educational data can be deceptive; a dummy rule that blindly predicts the positive class scores ~60.2% accuracy. This highlights why calibration (ECE), Log Loss, and ROC-AUC are far more informative than raw accuracy alone.

2. **Ceiling Analysis (Bayes-Optimal Oracle Benchmark):**
   - **Method:** Computed via `ml/ceiling_analysis.py`. The oracle queries the true latent proficiency $\mu_{s, k}$ and item difficulty $d_q$ using the exact generative 3PL IRT formula at every step.
   - **Performance on Sequential Transitions (N = 2,726):**
     - **Oracle ROC-AUC:** **0.6892**
     - **Oracle Log Loss:** **0.6186**
     - **Oracle Accuracy:** **0.6592**
   - **Performance on Full Test Cohort (N = 2,771):**
     - **Oracle ROC-AUC:** **0.6879**
     - **Oracle Log Loss:** **0.6193**
     - **Oracle Accuracy:** **0.6575**
   - **Theoretical Insight:** Even an omniscient oracle that knows the student's true latent ability vector and the underlying simulation equations cannot exceed ROC-AUC ~ 0.6892. This ceiling arises from the irreducible stochasticity of human cognitive performance: guessing ($c = 0.15$), slipping ($s = 0.05$), and logistic variance. Consequently, Logistic Regression (AUC = 0.6283) captures over 68% of the theoretically learnable information gap between the trivial baseline (0.5000) and the theoretical oracle ceiling (0.6892).

---

## 6. Calibration & Reliability Analysis

Educational recommendation systems must produce reliable confidence estimates. The **Expected Calibration Error (ECE)** was computed across 10 probability bins $[0, 0.1], (0.1, 0.2], \dots, (0.9, 1.0]$:

- **Logistic Regression (ECE = 0.0147):** Exceptionally well-calibrated; a predicted success probability of 0.70 maps to an empirical accuracy of ~69.4%.
- **Random Forest (ECE = 0.0353):** Demonstrates slight probability compression toward the center (0.4–0.6) typical of ensemble averaging.
- **DKT GRU (ECE = 0.0526):** Regularized via early stopping and weight decay, achieving substantially improved calibration over unregularized runs (down from 0.1215).

**Ethical Limitation:** Predicted probabilities must never be interpreted as clinical psychological measurements of student intelligence. They represent conditional statistical expectations under a simplified assessment model.

---

## 7. Adaptive Selection & Practice Composition

StudyMind converts statistical predictions into an actionable 10-question quiz composition:

1. **Diagnostic Initial Survey:** For learners with fewer than 5 recorded interactions, the system generates a balanced diagnostic quiz across all topics in the curriculum.
2. **Adaptive Practice Composition:** For active learners, topic priority weights are computed as $w_k = (1.0 - \hat{p}_k)$.
   - The top 1–2 topics requiring practice receive **60% to 70%** (6–7 questions).
   - Remaining topics receive **30% to 40%** (3–4 questions) for broad curriculum revision, preventing student burnout and avoiding overfitting practice to a single topic.
3. **Transparency Rationale:** The UI explicitly displays the pedagogical rationale behind each question distribution.

---

## 8. Limitations & Future Roadmap

1. **Synthetic Telemetry:** Current experiments utilize an IRT synthetic benchmark. Future iterations will train on telemetry collected from human educational deployments.
2. **Simulated vs. Real Students Discrepancy:** The DKT GRU and baseline models were trained on simulated students generated via an Item Response Theory (IRT) model, but in the live interactive Streamlit application, the predictor is applied to real student interactions. While the explicit topic-to-skill mapping and empirical accuracy fallbacks provide robust guardrails, models trained on synthetic Markov/IRT trajectories may not fully capture the idiosyncratic learning patterns, fatigue, or cognitive strategies of actual human learners.
3. **Cold-Start Latency:** Initial interactions have higher uncertainty; incorporating pre-quiz diagnostic self-assessments could accelerate cold-start adaptation.
4. **Transformer Knowledge Tracing (SAKT/AKT):** Exploring Self-Attentive Knowledge Tracing (SAKT) to replace recurrent units with monotonic attention mechanisms over student interaction history.
5. **Multimodal Feedback:** Expanding LLM question generation to include interactive follow-up tutoring dialogues and code execution feedback.

---

## 9. Conclusion

StudyMind demonstrates a complete, academically sound prototype of an adaptive learning system. By uniting secure student isolation, rigorous 10-question quiz validation, leakage-safe machine learning benchmarks, and transparent growth-oriented feedback, StudyMind bridges the gap between predictive knowledge tracing research and intuitive classroom web applications.
