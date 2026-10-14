"""
StudyMindAI Interactive Tutor endpoints with real-time WebSocket streaming.
Provides personalized, human-like tutoring, conceptual explanations, and analogies.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.schemas import TutorChatRequest
from database.db import DatabaseManager, DEFAULT_DB_PATH

load_dotenv()

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])

# Grounded knowledge base for comprehensive, high-quality answers
TUTOR_KNOWLEDGE_BASE = {
    "supervised learning": (
        "**Supervised Learning** is where an algorithm learns from labeled training examples — "
        "every input comes with its correct answer (ground truth).\n\n"
        "💡 **Analogy:** Think of studying with flashcards where questions are on the front and answers are on the back.\n\n"
        "**Key Algorithms:**\n"
        "- Linear & Logistic Regression\n"
        "- Decision Trees & Random Forests\n"
        "- Support Vector Machines (SVM)\n"
        "- Neural Networks"
    ),
    "deep learning": (
        "**Deep Learning** uses multi-layered artificial neural networks to learn representations of data with multiple levels of abstraction.\n\n"
        "💡 **Core Components:**\n"
        "- **Layers:** Input layer, hidden layers (Dense, Conv, Recurrent, Transformer), and output layer.\n"
        "- **Activation Functions:** ReLU, GELU, Sigmoid, Softmax.\n"
        "- **Backpropagation:** Calculates gradients of the loss function with respect to weights using the chain rule.\n"
        "- **Optimizers:** Adam, SGD with momentum, RMSprop."
    ),
    "l1 vs l2": (
        "**L1 (Lasso) vs L2 (Ridge) Regularization:**\n\n"
        "Both prevent overfitting by penalizing large model weights, but in different ways:\n\n"
        "1. **L1 Regularization (Lasso):**\n"
        "   - Adds the sum of *absolute values* of weights: `Loss + λ Σ|w|`\n"
        "   - Drives less important feature weights completely to **0**, performing automatic feature selection!\n\n"
        "2. **L2 Regularization (Ridge):**\n"
        "   - Adds the sum of *squared values* of weights: `Loss + λ Σw²`\n"
        "   - Shrinks weights smoothly toward 0 without making them strictly zero.\n\n"
        "💡 **Analogy:** L1 is like packing a suitcase and tossing non-essential items out entirely. L2 is like vacuum-compressing all your clothes so everything shrinks evenly."
    ),
    "regularization": (
        "**Regularization** techniques prevent models from memorizing noise in the training set (overfitting) "
        "so they generalize well to unseen test data.\n\n"
        "- **L1 (Lasso):** Drives weights to exact zero (sparse models).\n"
        "- **L2 (Ridge):** Shrinks weights proportionally.\n"
        "- **Dropout (Neural Nets):** Randomly deactivates a fraction of neurons during each training step.\n"
        "- **Early Stopping:** Halts training when validation loss begins to increase."
    ),
    "evaluation metrics": (
        "**Model Evaluation Metrics:**\n\n"
        "- **Accuracy:** `(TP + TN) / Total`. Misleading when classes are imbalanced!\n"
        "- **Precision:** `TP / (TP + FP)`. How many of our positive predictions were actually correct? (Crucial for spam filters).\n"
        "- **Recall (Sensitivity):** `TP / (TP + FN)`. How many of the actual positives did we catch? (Crucial for medical diagnoses).\n"
        "- **F1-Score:** Harmonic mean of Precision and Recall: `2 * (Precision * Recall) / (Precision + Recall)`.\n"
        "- **ROC-AUC:** Area Under the Receiver Operating Characteristic curve — measures ranking quality across all thresholds."
    ),
    "expected calibration error": (
        "**Expected Calibration Error (ECE):**\n\n"
        "ECE measures how closely a model's predicted confidence probabilities match its true empirical accuracy.\n\n"
        "- If a model predicts an event with **80% confidence**, it should be correct **80% of the time**.\n"
        "- **How it's computed:** Group predictions into `M` bins by confidence score, compute the absolute difference between average confidence and accuracy in each bin, and weight by bin size:\n"
        "  `ECE = Σ ( |acc(B_m) - conf(B_m)| * |B_m| / N )`\n\n"
        "💡 **Analogy:** A weather forecaster who predicts 90% chance of rain on 100 days. If it rains on 90 of those days, the forecaster is well-calibrated (low ECE)!"
    ),
    "ece": (
        "**Expected Calibration Error (ECE):**\n\n"
        "ECE measures how well calibrated model confidence scores are compared to actual accuracy.\n\n"
        "- **Well-calibrated:** When the model is 70% confident, it is right 70% of the time.\n"
        "- **Overconfident:** Often happens in deep neural networks where softmax outputs reach 99% confidence even when making errors.\n"
        "- **Fixes:** Temperature scaling, Platt scaling, or isotonic regression."
    ),
    "overfitting": (
        "**Overfitting vs Underfitting:**\n\n"
        "- **Overfitting (High Variance):** Model memorizes training noise rather than learning general patterns. Performs great on training data, poorly on test data.\n"
        "  *Remedies:* Add L1/L2 regularization, reduce model capacity, add Dropout, use cross-validation, get more data.\n"
        "- **Underfitting (High Bias):** Model is too simplistic to capture underlying trends (e.g., fitting a straight line to quadratic data).\n"
        "  *Remedies:* Increase model complexity, engineer richer features, reduce regularization."
    ),
    "bias variance": (
        "**The Bias-Variance Tradeoff:**\n\n"
        "Total Error = `Bias² + Variance + Irreducible Noise`\n\n"
        "- **Bias:** Error from erroneous assumptions in the learning algorithm (underfitting).\n"
        "- **Variance:** Sensitivity to small fluctuations in the training set (overfitting).\n\n"
        "💡 **Goal:** Find the sweet spot that minimizes total error on unseen data."
    ),
    "gradient descent": (
        "**Gradient Descent Optimization:**\n\n"
        "An iterative first-order optimization algorithm for finding a local minimum of a differentiable objective function.\n\n"
        "**Update Rule:** `w = w - η * ∇L(w)`\n"
        "- `η` is the **learning rate** (step size).\n"
        "- `∇L(w)` is the gradient (direction of steepest ascent).\n\n"
        "**Variants:**\n"
        "- **Batch GD:** Uses entire dataset per step (slow, stable).\n"
        "- **Stochastic GD (SGD):** Uses 1 sample per step (fast, noisy).\n"
        "- **Mini-batch GD:** Uses a batch (e.g. 32, 64) per step (best of both worlds, hardware-accelerated)."
    ),
    "dynamic programming": (
        "**Dynamic Programming (DP)** solves complex problems by breaking them down into simpler, overlapping subproblems and storing their solutions.\n\n"
        "💡 **Analogy:** If I write `1 + 1 + 1 + 1` on a board and ask 'What does that equal?', you count to 4. "
        "If I add another `+ 1` at the end, you don't recount from scratch — you remember 4 and say '5'! That is DP.\n\n"
        "**Two Approaches:**\n"
        "1. **Top-Down (Memoization):** Recursive approach that caches computed results in a dictionary or array.\n"
        "2. **Bottom-Up (Tabulation):** Iterative approach that fills a table starting from base cases."
    ),
    "big o": (
        "**Big O Notation** describes how the runtime or memory requirement of an algorithm grows as the input size `n` increases.\n\n"
        "**Complexity Hierarchy (Fastest to Slowest):**\n"
        "- **O(1) Constant:** Hash map lookup, accessing an array element by index.\n"
        "- **O(log n) Logarithmic:** Binary search.\n"
        "- **O(n) Linear:** Simple loop through a list.\n"
        "- **O(n log n) Linearithmic:** Merge Sort, Quick Sort (average), Timsort.\n"
        "- **O(n²) Quadratic:** Nested loops, Bubble Sort.\n"
        "- **O(2ⁿ) Exponential:** Recursive Fibonacci without memoization."
    ),
    "binary search": (
        "**Binary Search:**\n\n"
        "Efficient algorithm for finding an item from a **sorted** list by repeatedly dividing the search interval in half.\n\n"
        "- **Time Complexity:** `O(log n)`\n"
        "- **Space Complexity:** `O(1)` iterative\n\n"
        "```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```"
    ),
    "bfs vs dfs": (
        "**Breadth-First Search (BFS) vs Depth-First Search (DFS):**\n\n"
        "- **BFS (Queue - FIFO):** Explores neighbors level by level. Guarantees the shortest path in unweighted graphs!\n"
        "- **DFS (Stack - LIFO / Recursion):** Plunges as deep down a branch as possible before backtracking. "
        "Great for maze solving, topological sorting, and cycle detection."
    ),
    "bfs": (
        "**Breadth-First Search (BFS):**\n\n"
        "Explores a graph level by level starting from a root node using a **Queue (FIFO)**.\n\n"
        "- **Guarantees:** Finds the shortest path in unweighted graphs.\n"
        "- **Time Complexity:** `O(V + E)` where V is vertices and E is edges.\n"
        "- **Space Complexity:** `O(V)` to hold the queue.\n\n"
        "💡 **Analogy:** Ripples expanding outwards in all directions when you drop a stone in water."
    ),
    "dfs": (
        "**Depth-First Search (DFS):**\n\n"
        "Traverses as deep as possible along each branch before backtracking, using a **Stack (LIFO)** or recursion.\n\n"
        "- **Applications:** Maze solving, detecting cycles, topological sorting, finding connected components.\n"
        "- **Time Complexity:** `O(V + E)`\n"
        "- **Space Complexity:** `O(h)` where h is max call stack depth."
    ),
    "trees": (
        "**Trees & Binary Search Trees (BST):**\n\n"
        "A Tree is a hierarchical data structure. In a **Binary Search Tree**:\n"
        "- All nodes in the left subtree have values strictly *less* than the parent node.\n"
        "- All nodes in the right subtree have values strictly *greater* than the parent node.\n\n"
        "This allows search, insertion, and deletion in **O(log n)** average time (or O(n) if unbalanced)."
    ),
    "graphs": (
        "**Graphs** represent networks of entities called **Vertices (Nodes)** connected by **Edges**.\n\n"
        "- **Representations:** Adjacency Matrix (great for dense graphs, O(V²) space) vs. Adjacency List (space-efficient, O(V + E)).\n"
        "- **Directed vs Undirected:** One-way streets vs two-way roads.\n"
        "- **Weighted vs Unweighted:** Edges carry costs (distances, latencies)."
    ),
    "generators": (
        "**Python Generators vs List Comprehensions:**\n\n"
        "- A list comprehension `[x**2 for x in range(1000000)]` computes and stores all 1,000,000 numbers in RAM immediately.\n"
        "- A generator `(x**2 for x in range(1000000))` or function with `yield` computes values **lazily on demand** (one by one), using almost zero memory!\n\n"
        "```python\ndef count_up(n):\n    for i in range(n):\n        yield i\n```"
    ),
    "object-oriented": (
        "**The Four Pillars of Object-Oriented Programming (OOP):**\n\n"
        "1. **Encapsulation:** Bundling data and methods together inside a class and restricting direct access.\n"
        "2. **Abstraction:** Hiding internal implementation complexities and exposing only clean interfaces.\n"
        "3. **Inheritance:** Creating new classes based on existing ones to share logic (`class Dog(Animal):`).\n"
        "4. **Polymorphism:** Allowing different classes to be treated through the same interface (e.g. `speak()` behaves differently for Dog and Cat)."
    ),
    "decorators": (
        "**Python Decorators:**\n\n"
        "A decorator is a function that takes another function as an argument, extends its behavior without modifying its source code, and returns a new function.\n\n"
        "```python\ndef timer_decorator(func):\n    def wrapper(*args, **kwargs):\n        import time\n        start = time.time()\n        result = func(*args, **kwargs)\n        print(f'{func.__name__} took {time.time() - start:.4f}s')\n        return result\n    return wrapper\n\n@timer_decorator\ndef compute():\n    return sum(i for i in range(100000))\n```"
    ),
    "probability": (
        "**Key Probability Foundations:**\n\n"
        "- **Normal Distribution:** Bell-shaped curve centered at mean μ with spread σ. Governed by the Central Limit Theorem.\n"
        "- **Bayes' Theorem:** `P(A|B) = P(B|A) * P(A) / P(B)`. Updates our prior belief with new observed evidence.\n"
        "- **Independence:** Two events are independent if `P(A and B) = P(A) * P(B)`."
    ),
    "hypothesis testing": (
        "**Hypothesis Testing in 3 Steps:**\n\n"
        "1. **State Hypotheses:** Null Hypothesis (H0: no difference) vs Alternative (H1: significant effect).\n"
        "2. **Compute p-value:** The probability of getting results at least as extreme as observed, assuming H0 is true.\n"
        "3. **Decision Rule:** If `p < 0.05` (significance level α), we reject H0 in favor of H1."
    ),
    "gru": (
        "**GRU (Gated Recurrent Unit):**\n\n"
        "A **GRU** is an efficient recurrent neural network (RNN) architecture designed to capture sequential dependencies in time-series and learning logs while preventing the vanishing gradient problem.\n\n"
        "💡 **Core Gating Mechanisms:**\n"
        "- **Update Gate ($z_t$):** Regulates how much of the previous hidden state memory to retain vs. replace: $z_t = \\sigma(W_z \\cdot [h_{t-1}, x_t] + b_z)$.\n"
        "- **Reset Gate ($r_t$):** Controls how much past information to forget before proposing a candidate state: $r_t = \\sigma(W_r \\cdot [h_{t-1}, x_t] + b_r)$.\n"
        "- **Candidate Hidden State ($\\tilde{h}_t$):** Proposes a new memory update using reset gate: $\\tilde{h}_t = \\tanh(W_h \\cdot [r_t \\odot h_{t-1}, x_t] + b_h)$.\n"
        "- **Final Hidden State ($h_t$):** Blends past memory with new candidate: $h_t = z_t \\odot h_{t-1} + (1 - z_t) \\odot \\tilde{h}_t$.\n\n"
        "💡 **Analogy:** Think of an update gate as deciding how much of yesterday's meeting notes to keep, and the reset gate as wiping parts of the whiteboard before starting a new discussion draft.\n\n"
        "**GRU vs. LSTM:**\n"
        "- GRU has **no separate cell state** (combines hidden state and cell state).\n"
        "- GRU uses **2 gates** instead of LSTM's 3 gates (input, forget, output).\n"
        "- Trains significantly faster and requires fewer parameters with comparable sequential modeling accuracy!"
    ),
    "gated recurrent unit": (
        "**Gated Recurrent Unit (GRU):**\n\n"
        "An optimized recurrent neural network (RNN) cell architecture designed for sequence modeling, natural language processing, and **Deep Knowledge Tracing (DKT)**.\n\n"
        "- **Update Gate:** Controls memory retention across sequential steps.\n"
        "- **Reset Gate:** Drops irrelevant past context.\n"
        "- **Advantage:** Mitigates vanishing gradients with faster training speed and fewer parameters than 3-gate LSTMs."
    ),
    "ai": (
        "**Artificial Intelligence (AI):**\n\n"
        "Artificial Intelligence is the branch of computer science focused on building computational systems capable of performing tasks that typically require human intelligence — including reasoning, pattern recognition, learning from experience, and autonomous decision-making.\n\n"
        "**Curriculum Hierarchy:**\n"
        "1. **Artificial Intelligence (Broadest):** Any computational system that perceives its environment and takes actions to maximize its chance of successfully achieving its goals.\n"
        "2. **Machine Learning (Subset):** Algorithms that improve automatically through experience and statistical data patterns without explicit hardcoded rules.\n"
        "3. **Deep Learning (Subfield of ML):** Deep multi-layer artificial neural networks (CNNs, RNNs/GRUs, Transformers) modeling representations directly from raw data.\n\n"
        "💡 **Core Paradigms:** Supervised learning (labeled data), Unsupervised learning (clustering & dimensionality reduction), and Reinforcement learning (agent-environment reward maximization)."
    ),
    "artificial intelligence": (
        "**Artificial Intelligence (AI):**\n\n"
        "The science and engineering of creating intelligent machines capable of reasoning, perceiving, and learning from experience.\n\n"
        "- **Narrow AI (ANI):** Specialized in specific tasks (e.g. recommendation systems, chess engines, Deep Knowledge Tracing).\n"
        "- **General AI (AGI):** Hypothetical machines with generalized human-level cognitive flexibility across all domains.\n"
        "- **Foundational Pillars:** Data structures, linear algebra, probability & statistics, and optimization algorithms."
    ),
    "neural network": (
        "**Artificial Neural Networks (ANN):**\n\n"
        "Computational architectures inspired by biological neural circuits in the human brain.\n\n"
        "**Fundamental Pipeline:**\n"
        "1. **Linear Transformation:** $z = W \\cdot x + b$\n"
        "2. **Non-Linear Activation:** $a = f(z)$ (e.g., ReLU, GELU, Sigmoid) introducing representation capacity for non-linear decision boundaries.\n"
        "3. **Loss Function:** Quantifies error between prediction and ground truth (Cross-Entropy or Mean Squared Error).\n"
        "4. **Backpropagation:** Computes analytical gradients via the chain rule to update weights iteratively using gradient descent (Adam, SGD)."
    ),
    "rnn": (
        "**Recurrent Neural Networks (RNN):**\n\n"
        "Neural networks designed specifically for processing sequential data (time-series, text, student learning logs).\n\n"
        "- **Mechanism:** Maintains an internal **hidden state vector** ($h_t$) passed from one time step to the next.\n"
        "- **Limitation:** Susceptible to vanishing or exploding gradients over long sequences.\n"
        "- **Modern Solution:** Gated variants like **GRUs** and **LSTMs**, or **Transformers**."
    ),
    "transformer": (
        "**The Transformer Architecture:**\n\n"
        "State-of-the-art deep learning architecture that relies on **Self-Attention** rather than sequential recurrence.\n\n"
        "- **Self-Attention:** Dynamically weighs the relevance of every token with respect to every other token in parallel.\n"
        "- **Formula:** $\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right) V$\n"
        "- **Advantages:** Highly parallelizable on GPUs, captures long-range context without vanishing gradients."
    ),
    "dkt": (
        "**Deep Knowledge Tracing (DKT):**\n\n"
        "DKT models student mastery dynamically using recurrent neural networks (specifically GRUs).\n\n"
        "**How StudyMindAI Uses DKT:**\n"
        "- Each question answered `(topic_id, is_correct)` is fed sequentially into the DKT GRU.\n"
        "- The model continuously updates its hidden representation of your skill state.\n"
        "- The output layer estimates your real-time mastery across all 15 curriculum topics, driving adaptive recommendations!"
    )
}


def _call_llm_tutor(message: str, display_name: str) -> Optional[str]:
    """
    Calls the configured LLM provider (Mistral, OpenRouter, OpenAI, Gemini)
    to generate an intelligent, context-aware pedagogical tutoring response.
    Returns None if offline or if the call fails, triggering grounded fallback.
    """
    llm_provider = os.getenv("LLM_PROVIDER", "offline").lower()
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if llm_provider == "offline":
        return None
    if not (mistral_key or openrouter_key or openai_key or gemini_key):
        return None

    is_mistral = (llm_provider == "mistral" or (mistral_key and not (openrouter_key or openai_key)))
    endpoint = None
    headers = {"Content-Type": "application/json"}
    model_name = os.getenv("MODEL_NAME")

    if is_mistral and mistral_key:
        api_key = mistral_key
        endpoint = "https://api.mistral.ai/v1/chat/completions"
        model_name = model_name or "ministral-3b-latest"
        headers["Authorization"] = f"Bearer {api_key}"
    elif openrouter_key or llm_provider == "openrouter":
        if not openrouter_key:
            return None
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        model_name = model_name or "nvidia/nemotron-3-ultra-550b-a55b:free"
        headers["Authorization"] = f"Bearer {openrouter_key}"
        headers["HTTP-Referer"] = "https://studymind.local"
        headers["X-Title"] = "StudyMind AI Study Coach"
    elif openai_key or llm_provider == "openai":
        if not openai_key:
            return None
        endpoint = "https://api.openai.com/v1/chat/completions"
        model_name = model_name or "gpt-4o-mini"
        headers["Authorization"] = f"Bearer {openai_key}"
    elif gemini_key or llm_provider == "gemini":
        if not gemini_key:
            return None
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    else:
        return None

    system_prompt = (
        f"You are StudyMindAI's friendly, encouraging, and expert AI Study Coach for student {display_name}. "
        f"StudyMindAI is an adaptive learning platform specializing in Computer Science, Machine Learning, Deep Learning, "
        f"Data Science, Python, Mathematics, and Algorithms. "
        f"When explaining technical terms (e.g. GRU / Gated Recurrent Unit, CNN, Transformers, Big O, DKT, Gradient Descent), "
        f"explain them strictly within the computer science and machine learning curriculum context unless the student specifies otherwise. "
        f"Provide clear, pedagogical explanations with intuitive analogies, key formulas or architecture points, "
        f"and clean Python code snippets where helpful. "
        f"Format your response neatly in GitHub-style Markdown with appropriate headers, bullet points, and code blocks. "
        f"Keep your tone warm, intellectual, and inspiring."
    )

    try:
        if "generativelanguage.googleapis.com" in (endpoint or ""):
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"{system_prompt}\n\nStudent question: {message}"}
                    ]
                }]
            }
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                res_json = resp.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": 0.5,
            "max_tokens": 800
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if choices and "message" in choices[0]:
                content = choices[0]["message"].get("content", "").strip()
                if content:
                    return content
        else:
            print(f"[StudyMind Tutor Notice] LLM returned status {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"[StudyMind Tutor Notice] LLM request notice ({e}); switching to grounded knowledge base.")

    return None


def generate_tutor_response(message: str, username: Optional[str] = "there", student_id: Optional[int] = None) -> str:
    """Generates warm, human-like, pedagogical replies tailored to the student."""
    msg = message.strip()
    msg_lower = msg.lower()

    # Determine student's name if available
    display_name = "there"
    if username and username.lower() not in ["there", "none", "null", "undefined"]:
        display_name = username.split()[0]

    if student_id:
        try:
            db = DatabaseManager(DEFAULT_DB_PATH)
            student = db.get_student_by_id(student_id)
            if student and student.display_name:
                display_name = student.display_name.split()[0]
        except Exception:
            pass

    # 1. Greetings
    greetings = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon", "howdy", "sup", "yo", "greetings"]
    clean_msg = "".join(c if c.isalnum() or c.isspace() else " " for c in msg_lower).strip()
    words = clean_msg.split()

    # Pure greeting check: matches "hi", "hello!", "hey tutor", "hi there", "hello alex", "hey"
    if words and words[0] in greetings:
        non_greeting_words = [
            w for w in words
            if w not in greetings and w not in ["there", "tutor", "bot", "assistant", "studymind", "ai", display_name.lower()]
        ]
        if len(non_greeting_words) == 0:
            return f"Hey {display_name}! 👋 How can I help you today? Ask me any question about Machine Learning, Python, Statistics, or Algorithms, and I'll explain it clearly!"

    # 2. Courtesy / Small Talk & Identity
    small_talk_queries = [
        "how are you", "who are you", "what can you do", "what is your name",
        "what's your name", "whats your name", "who made you", "tell me about yourself",
        "who are u", "what is your role", "your name"
    ]
    if any(phrase in msg_lower for phrase in small_talk_queries):
        return (
            f"Hey {display_name}! 🎓 I'm your **StudyMindAI Study Coach**!\n\n"
            f"I'm your personalized adaptive AI tutor for **Machine Learning, Deep Learning, Python, Data Science, and Algorithms**.\n\n"
            f"Here is how I can support your learning:\n"
            f"- 💡 **Explain Concepts:** Break down complex topics with simple, intuitive analogies.\n"
            f"- 💻 **Code Examples:** Write clean Python snippets and demonstrate data structures.\n"
            f"- 🎯 **Quiz Deconstruction:** Explain question rationales, hints, and exam strategies.\n"
            f"- 📈 **Personalized Revision:** Target your weaker skills identified by our Deep Knowledge Tracing engine.\n\n"
            f"What topic would you like to explore or practice today?"
        )

    if any(phrase in msg_lower for phrase in ["thanks", "thank you", "thx", "awesome", "perfect", "great"]):
        return f"You're very welcome, {display_name}! 😊 Keep up the awesome learning momentum. Let me know whenever you'd like to explore another question!"

    # 3. Practice / Quiz intent
    if any(phrase in msg_lower for phrase in ["start quiz", "take quiz", "practice quiz", "give me a quiz", "start practice"]):
        return (
            f"Ready for a practice session, {display_name}? 🎯\n\n"
            f"You can jump straight into the **Practice Quiz** section from the sidebar! "
            f"StudyMindAI will tailor 10 questions to focus on your weaker topics while giving you a fresh mix of revision."
        )

    # 4. Online LLM generation (when configured with API key)
    llm_reply = _call_llm_tutor(msg, display_name=display_name)
    if llm_reply:
        return llm_reply

    # 5. Check domain concepts in grounded knowledge base (offline / fallback)
    prefix = ""
    if words and words[0] in greetings:
        prefix = f"Hey {display_name}! 👋 Great question.\n\n"

    for key, content in TUTOR_KNOWLEDGE_BASE.items():
        if key in msg_lower:
            return f"{prefix}### 💡 {key.title()}\n\n{content}\n\n---\n*Need an example or a follow-up explanation? Just ask!*"

    # 6. Intelligent Pedagogical Fallback (offline mode)
    return (
        f"Hey {display_name}! 🧠 Let's explore **{msg}** together.\n\n"
        f"**Conceptual Framework:**\n"
        f"When studying this topic in Computer Science and Machine Learning, consider these essential dimensions:\n\n"
        f"1. **Core Problem Formulation:** What exact mathematical or computational problem does this address?\n"
        f"2. **Algorithm & Architecture:** What is the input representation, transformation step, and objective function?\n"
        f"3. **Tradeoffs & Complexity:** How does it scale with data volume (time/space complexity) and how does it compare to baseline alternatives?\n"
        f"4. **Hands-On Verification:** How can you validate it with a minimal test in Python?\n\n"
        f"💡 **Next Step:** You can ask me to generate a code snippet, explain an analogy, or head to the **Practice Quiz** to test your active recall on this!"
    )


# --- HTTP REST Endpoint ---
@router.post("/chat")
def chat_with_tutor(payload: TutorChatRequest):
    reply = generate_tutor_response(payload.message, student_id=payload.student_id)
    return {
        "reply": reply,
        "topic": payload.topic or "Study Guidance"
    }


# --- Real-Time WebSocket Endpoint ---
@router.websocket("/ws")
async def tutor_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time AI tutor messaging with streaming chunk delivery.
    """
    await websocket.accept()
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except Exception:
                data = {"message": data_text}

            user_msg = data.get("message", "")
            username = data.get("username", "there")
            student_id = data.get("student_id")

            # 1. Generate response text (run in threadpool so it does not block the async event loop)
            full_reply = await asyncio.to_thread(generate_tutor_response, user_msg, username, student_id)

            # 2. Send start event
            await websocket.send_json({"type": "start"})

            # 3. Stream chunks with natural typing rhythm
            words = full_reply.split(" ")
            chunk_size = 2
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk
                })
                await asyncio.sleep(0.02)  # Smooth streaming animation

            # 4. Send completion event
            await websocket.send_json({
                "type": "done",
                "reply": full_reply
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

