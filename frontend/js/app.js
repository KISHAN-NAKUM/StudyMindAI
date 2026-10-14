/**
 * StudyMindAI Single Page Application Core Controller
 * High-performance, reactive UI architecture with dynamic animations,
 * friendly human wording, interactive skill simulator, and audio feedback.
 */

import { api, tutorWS } from './api.js';
import { sound } from './audio.js';
import { initAmbientParticles } from './particles.js';
import { renderRadarChart, renderTimelineChart } from './charts.js';

// Global Application State
const state = {
  user: null,
  activeView: 'dashboard',
  subjects: [],
  quiz: {
    active: false,
    sessionToken: null,
    subjectId: null,
    subjectName: '',
    mode: 'adaptive',
    difficulty: 'Medium',
    rationale: '',
    questions: [],
    answers: {},
    currentIdx: 0,
    startTime: 0,
    timerInterval: null
  },
  lastResults: null,
  simulatorSteps: []
};

// --- Toast Notification Center ---
export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span style="font-size: 1.1rem;">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  if (type === 'success') sound.playSelect();
  else if (type === 'error') sound.playTone(300, 'sawtooth', 0.15, 0.08);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- View Navigation & Routing ---
function switchView(viewName) {
  state.activeView = viewName;
  sound.playClick();

  // Update sidebar active link
  document.querySelectorAll('.nav-item').forEach((item) => {
    if (item.dataset.view === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Human-friendly topbar titles and descriptions
  const titles = {
    dashboard: { 
      title: 'Learning Dashboard', 
      desc: 'See how you are doing and discover personalized practice recommendations' 
    },
    quiz: { 
      title: 'Practice Quiz', 
      desc: '10 quick questions customized to strengthen your skills' 
    },
    results: { 
      title: 'Quiz Results & Review', 
      desc: 'Check your score, celebrate progress, and review helpful explanations' 
    },
    analytics: { 
      title: 'My Progress & Skills', 
      desc: 'See all topics you have practiced and review past quizzes' 
    },
    simulator: { 
      title: 'AI Practice Lab', 
      desc: 'Interactive playground: see how each answer helps our AI understand your skills' 
    },
    tutor: { 
      title: 'AI Study Coach', 
      desc: 'Ask questions anytime, get simple analogies, and learn at your own pace' 
    }
  };

  const info = titles[viewName] || { title: 'StudyMindAI', desc: 'Smart Adaptive Learning' };
  const titleEl = document.getElementById('topbar-view-title');
  const descEl = document.getElementById('topbar-view-desc');
  if (titleEl) titleEl.innerText = info.title;
  if (descEl) descEl.innerText = info.desc;

  renderCurrentView();
}

function renderCurrentView() {
  const container = document.getElementById('view-container');
  if (!container) return;
  container.innerHTML = '';

  switch (state.activeView) {
    case 'dashboard':
      renderDashboard(container);
      break;
    case 'quiz':
      if (state.quiz.active) renderQuizActive(container);
      else renderQuizSetup(container);
      break;
    case 'results':
      renderResults(container);
      break;
    case 'analytics':
      renderAnalytics(container);
      break;
    case 'simulator':
      renderSimulator(container);
      break;
    case 'tutor':
      renderTutorView(container);
      break;
    default:
      renderDashboard(container);
  }
}

// ==========================================================================
// 1. Sign In / Registration View
// ==========================================================================
function renderAuth() {
  document.getElementById('app-sidebar').style.display = 'none';
  document.getElementById('app-topbar').style.display = 'none';
  document.getElementById('tutor-drawer-wrapper').style.display = 'none';

  const container = document.getElementById('view-container');
  container.innerHTML = `
    <div style="max-width: 480px; margin: 60px auto; text-align: center;">
      <div class="brand-icon" style="width: 58px; height: 58px; font-size: 2rem; margin: 0 auto 20px auto;">🧠</div>
      <h1 style="font-family: var(--font-heading); font-size: 2.6rem; font-weight: 800; color: #0f172a; margin-bottom: 8px;">
        StudyMind<span style="color: var(--primary);">AI</span>
      </h1>
      <p style="color: var(--text-muted); font-size: 1.05rem; margin-bottom: 32px;">
        Your personalized, student-friendly practice companion.
      </p>

      <div class="glass-card" style="text-align: left;">
        <div style="display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <button class="btn btn-secondary" id="tab-login" style="flex: 1; border-color: var(--primary); background: #eef2ff; color: var(--primary);">🔑 Sign In</button>
          <button class="btn btn-secondary" id="tab-register" style="flex: 1;">📝 Create Account</button>
        </div>

        <!-- Sign In Form -->
        <div id="form-login">
          <div style="margin-bottom: 16px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px;">Username</label>
            <input type="text" id="login-username" class="tutor-input" style="width: 100%;" placeholder="e.g. demo_student" value="demo_student">
          </div>
          <div style="margin-bottom: 24px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px;">Password</label>
            <input type="password" id="login-password" class="tutor-input" style="width: 100%;" placeholder="••••••••" value="password123">
          </div>
          <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <button class="btn btn-primary" id="btn-login-submit" style="flex: 1;">Sign In</button>
            <button class="btn btn-secondary" id="btn-demo-login" style="flex: 1; background: #eef2ff; border-color: var(--primary); color: var(--primary);">⚡ Try as Demo Learner</button>
          </div>
          <p style="font-size: 0.82rem; color: var(--text-dim); text-align: center;">
            💡 Quick explore: Click <strong>Try as Demo Learner</strong> to explore with student sample records!
          </p>
        </div>

        <!-- Register Form -->
        <div id="form-register" style="display: none;">
          <div style="margin-bottom: 14px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px;">Your Name</label>
            <input type="text" id="reg-name" class="tutor-input" style="width: 100%;" placeholder="e.g. Maya Patel">
          </div>
          <div style="margin-bottom: 14px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px;">Choose a Username</label>
            <input type="text" id="reg-username" class="tutor-input" style="width: 100%;" placeholder="e.g. mayapatel">
          </div>
          <div style="margin-bottom: 24px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 6px;">Create Password</label>
            <input type="password" id="reg-password" class="tutor-input" style="width: 100%;" placeholder="At least 6 characters">
          </div>
          <button class="btn btn-primary" id="btn-reg-submit" style="width: 100%;">Create Account & Get Started</button>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const formLogin = document.getElementById('form-login');
  const formRegister = document.getElementById('form-register');

  tabLogin.onclick = () => {
    sound.playClick();
    tabLogin.style.borderColor = 'var(--primary)';
    tabLogin.style.background = '#eef2ff';
    tabLogin.style.color = 'var(--primary)';
    tabRegister.style.borderColor = 'transparent';
    tabRegister.style.background = '#f8fafc';
    tabRegister.style.color = 'var(--text-main)';
    formLogin.style.display = 'block';
    formRegister.style.display = 'none';
  };

  tabRegister.onclick = () => {
    sound.playClick();
    tabRegister.style.borderColor = 'var(--primary)';
    tabRegister.style.background = '#eef2ff';
    tabRegister.style.color = 'var(--primary)';
    tabLogin.style.borderColor = 'transparent';
    tabLogin.style.background = '#f8fafc';
    tabLogin.style.color = 'var(--text-main)';
    formRegister.style.display = 'block';
    formLogin.style.display = 'none';
  };

  // Demo Login
  document.getElementById('btn-demo-login').onclick = async () => {
    try {
      sound.playClick();
      const res = await api.demoLogin();
      setUserSession(res.student);
      showToast(`Welcome, ${res.student.display_name}!`, 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  // Manual Login
  document.getElementById('btn-login-submit').onclick = async () => {
    const user = document.getElementById('login-username').value.trim();
    const pass = document.getElementById('login-password').value.trim();
    if (!user || !pass) {
      showToast('Please enter your username and password', 'error');
      return;
    }
    try {
      sound.playClick();
      const res = await api.login(user, pass);
      setUserSession(res.student);
      showToast(`Welcome back, ${res.student.display_name}!`, 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  // Register
  document.getElementById('btn-reg-submit').onclick = async () => {
    const name = document.getElementById('reg-name').value.trim();
    const user = document.getElementById('reg-username').value.trim();
    const pass = document.getElementById('reg-password').value.trim();
    if (!name || !user || !pass) {
      showToast('Please fill out all registration fields', 'error');
      return;
    }
    try {
      sound.playClick();
      const res = await api.register(user, name, pass);
      setUserSession(res.student);
      showToast('Account created successfully!', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };
}

function setUserSession(student) {
  state.user = student;
  localStorage.setItem('studymind_user', JSON.stringify(student));

  document.getElementById('app-sidebar').style.display = 'flex';
  document.getElementById('app-topbar').style.display = 'flex';
  document.getElementById('tutor-drawer-wrapper').style.display = 'block';

  document.getElementById('sidebar-name').innerText = student.display_name;
  document.getElementById('sidebar-avatar').innerText = student.display_name.charAt(0).toUpperCase();

  // Personalize drawer welcome message
  const drawerMsg = document.getElementById('tutor-messages');
  if (drawerMsg) {
    const firstName = student.display_name.split(' ')[0];
    drawerMsg.innerHTML = `
      <div class="msg-bubble msg-tutor">
        Hey ${firstName}! 👋 I'm your AI Study Coach. Ask me any question or request help preparing for your quizzes!
      </div>
    `;
  }

  sound.playChime();
  switchView('dashboard');
}

// ==========================================================================
// 2. Learning Dashboard View
// ==========================================================================
async function renderDashboard(container) {
  const firstName = state.user ? state.user.display_name.split(' ')[0] : 'Learner';

  container.innerHTML = `
    <!-- Welcoming Hero Note -->
    <div style="margin-bottom: 24px;">
      <h2 style="font-family: var(--font-heading); font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-bottom: 4px;">
        Welcome back, ${firstName}! 👋
      </h2>
      <p style="color: var(--text-muted); font-size: 0.95rem;">
        Here is your personalized learning overview and recommended next steps.
      </p>
    </div>

    <!-- Quick Stats Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">Quizzes Completed</span>
          <div class="kpi-icon" style="background: #eef2ff; color: var(--primary);">📝</div>
        </div>
        <div class="kpi-val" id="kpi-quizzes">--</div>
        <div class="kpi-subtext">Practice sessions finished</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">Average Score</span>
          <div class="kpi-icon" style="background: #ecfdf5; color: var(--accent-emerald);">🎯</div>
        </div>
        <div class="kpi-val" id="kpi-accuracy">--%</div>
        <div class="kpi-subtext">Overall accuracy across all questions</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">Questions Practiced</span>
          <div class="kpi-icon" style="background: #e0f2fe; color: var(--accent-cyan);">⚡</div>
        </div>
        <div class="kpi-val" id="kpi-questions">--</div>
        <div class="kpi-subtext">Total questions answered so far</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">Mastered Topics</span>
          <div class="kpi-icon" style="background: #f5f3ff; color: var(--secondary);">🏆</div>
        </div>
        <div class="kpi-val" id="kpi-mastered">--</div>
        <div class="kpi-subtext">Strong topics with 75%+ score</div>
      </div>
    </div>

    <!-- AI Personalized Practice Recommendation Card -->
    <div class="glass-card" style="margin-bottom: 28px; border-left: 4px solid var(--primary); background: #ffffff;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 280px;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span class="badge badge-indigo">Recommended by AI Coach</span>
            <span id="rec-subject-badge" class="badge badge-amber">Subject Focus</span>
          </div>
          <h3 style="font-family: var(--font-heading); font-size: 1.45rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;" id="rec-title">
            What to Practice Next
          </h3>
          <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5;" id="rec-rationale">
            Analyzing your recent practice to give you the most helpful 10 questions...
          </p>
        </div>
        <div>
          <button class="btn btn-primary" id="btn-start-recommended" style="padding: 12px 24px; font-size: 1rem;">
            <span>🚀 Start 10-Question Practice</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 24px;">
      
      <!-- Topic Strengths Radar -->
      <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3 style="font-family: var(--font-heading); font-size: 1.2rem; font-weight: 700; color: #0f172a;">Topic Strengths</h3>
            <p style="font-size: 0.82rem; color: var(--text-muted);">See how confident you are in each area</p>
          </div>
          <select id="radar-subject-select" class="tutor-input" style="padding: 6px 12px; font-size: 0.82rem; width: auto;"></select>
        </div>
        <div style="height: 320px; position: relative;">
          <canvas id="canvas-radar" style="width: 100%; height: 100%;"></canvas>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-dim); text-align: center; margin-top: 10px;">
          💡 Green dashed circle is your 70% target score. Practice topics inside the circle to grow!
        </p>
      </div>

      <!-- Score Trajectory -->
      <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3 style="font-family: var(--font-heading); font-size: 1.2rem; font-weight: 700; color: #0f172a;">Your Practice Progress</h3>
            <p style="font-size: 0.82rem; color: var(--text-muted);">How your quiz scores are improving over time</p>
          </div>
          <span class="badge badge-emerald">Live Progress</span>
        </div>
        <div style="height: 320px; position: relative;">
          <canvas id="canvas-timeline" style="width: 100%; height: 100%;"></canvas>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-dim); text-align: center; margin-top: 10px;">
          📈 Each point represents a completed quiz. Green line shows the 70% proficiency goal.
        </p>
      </div>
    </div>
  `;

  // Fetch telemetry
  try {
    const overview = await api.getOverview(state.user.id);
    document.getElementById('kpi-quizzes').innerText = overview.total_quizzes;
    document.getElementById('kpi-accuracy').innerText = `${overview.avg_accuracy}%`;
    document.getElementById('kpi-questions').innerText = overview.total_questions;
    document.getElementById('kpi-mastered').innerText = `${overview.mastered_topics} / 15`;

    if (overview.recommendation) {
      document.getElementById('rec-subject-badge').innerText = overview.recommendation.subject_name;
      document.getElementById('rec-rationale').innerText = overview.recommendation.rationale;
      document.getElementById('btn-start-recommended').onclick = () => {
        launchAdaptiveQuiz(overview.recommendation.subject_id, overview.recommendation.subject_name);
      };
    }

    // Populate Subjects & Radar
    const subjects = await api.getSubjects();
    state.subjects = subjects;
    const select = document.getElementById('radar-subject-select');
    subjects.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.innerText = s.name;
      select.appendChild(opt);
    });

    const updateRadar = async (subjId) => {
      const mastery = await api.getMastery(state.user.id, subjId);
      if (mastery && mastery.length > 0) {
        renderRadarChart('canvas-radar', mastery[0].topics);
      }
    };

    if (subjects.length > 0) {
      updateRadar(subjects[0].id);
      select.onchange = (e) => updateRadar(e.target.value);
    }

    // Populate Progress Curve
    const timelineData = await api.getTimeline(state.user.id);
    renderTimelineChart('canvas-timeline', timelineData);

  } catch (err) {
    showToast('Failed to load dashboard: ' + err.message, 'error');
  }
}

// ==========================================================================
// 3. Practice Quiz Setup & Arena View
// ==========================================================================
async function renderQuizSetup(container) {
  container.innerHTML = `
    <div style="max-width: 680px; margin: 20px auto;">
      <div class="glass-card">
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 20px;">
          <div class="brand-icon" style="width: 44px; height: 44px; font-size: 1.3rem;">🎯</div>
          <div>
            <h2 style="font-family: var(--font-heading); font-size: 1.6rem; font-weight: 700; color: #0f172a;">Start a Practice Quiz</h2>
            <p style="font-size: 0.88rem; color: var(--text-muted);">Choose what you want to practice — exactly 10 questions every time.</p>
          </div>
        </div>

        <div style="margin-bottom: 20px;">
          <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 8px;">Subject</label>
          <select id="quiz-subj-select" class="tutor-input" style="width: 100%;"></select>
        </div>

        <div style="margin-bottom: 20px;">
          <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 8px;">Topic</label>
          <select id="quiz-topic-select" class="tutor-input" style="width: 100%;">
            <option value="">All Topics (Smart Mix recommended)</option>
          </select>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 28px;">
          <div>
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 8px;">Practice Mode</label>
            <select id="quiz-mode-select" class="tutor-input" style="width: 100%;">
              <option value="adaptive">Adaptive Mode (Focuses on weaker topics)</option>
              <option value="balanced">Equal Survey Mode (Balanced across all topics)</option>
            </select>
          </div>
          <div>
            <label style="font-size: 0.88rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 8px;">Difficulty</label>
            <select id="quiz-diff-select" class="tutor-input" style="width: 100%;">
              <option value="Medium">Standard (Recommended)</option>
              <option value="Easy">Beginner Friendly</option>
              <option value="Hard">Challenge</option>
            </select>
          </div>
        </div>

        <button class="btn btn-primary" id="btn-generate-quiz" style="width: 100%; padding: 14px; font-size: 1.05rem;">
          <span>⚡ Start 10-Question Quiz</span>
        </button>
      </div>
    </div>
  `;

  try {
    const subjects = await api.getSubjects();
    state.subjects = subjects;
    const subjSelect = document.getElementById('quiz-subj-select');
    const topicSelect = document.getElementById('quiz-topic-select');

    subjects.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.innerText = s.name;
      subjSelect.appendChild(opt);
    });

    const populateTopics = (subjId) => {
      const match = subjects.find((s) => s.id == subjId);
      topicSelect.innerHTML = '<option value="">All Topics (Smart Mix recommended)</option>';
      if (match && match.topics) {
        match.topics.forEach((t) => {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.innerText = t.name;
          topicSelect.appendChild(opt);
        });
      }
    };

    if (subjects.length > 0) {
      populateTopics(subjects[0].id);
      subjSelect.onchange = (e) => populateTopics(e.target.value);
    }

    document.getElementById('btn-generate-quiz').onclick = async () => {
      const sId = parseInt(subjSelect.value);
      const tId = topicSelect.value ? parseInt(topicSelect.value) : null;
      const mode = document.getElementById('quiz-mode-select').value;
      const diff = document.getElementById('quiz-diff-select').value;

      launchAdaptiveQuiz(sId, subjects.find((s) => s.id === sId)?.name, tId, mode, diff);
    };

  } catch (err) {
    showToast('Failed to load quiz options: ' + err.message, 'error');
  }
}

async function launchAdaptiveQuiz(subjectId, subjectName, topicId = null, mode = 'adaptive', difficulty = 'Medium') {
  showToast('Preparing your 10 practice questions...', 'info');
  try {
    sound.playClick();
    const res = await api.generateQuiz({
      subject_id: subjectId,
      topic_id: topicId,
      mode,
      difficulty,
      student_id: state.user.id
    });

    state.quiz = {
      active: true,
      sessionToken: res.session_token,
      subjectId: res.subject_id,
      subjectName: res.subject_name,
      mode: res.mode,
      difficulty: res.difficulty,
      rationale: res.rationale,
      questions: res.questions,
      answers: {},
      currentIdx: 0,
      startTime: Date.now(),
      timerInterval: null
    };

    sound.playCelebrate();
    switchView('quiz');
  } catch (err) {
    showToast('Failed to start quiz: ' + err.message, 'error');
  }
}

function renderQuizActive(container) {
  const qState = state.quiz;
  const currQ = qState.questions[qState.currentIdx];
  const totalQ = qState.questions.length;
  const selectedAns = qState.answers[qState.currentIdx] || '';

  const elapsedSeconds = Math.floor((Date.now() - qState.startTime) / 1000);
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  container.innerHTML = `
    <!-- Top Header -->
    <div class="quiz-header">
      <div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <h2 style="font-family: var(--font-heading); font-size: 1.5rem; font-weight: 700; color: #0f172a;">
            ${qState.subjectName}
          </h2>
          <span class="badge badge-indigo">${qState.mode === 'adaptive' ? 'Adaptive Practice' : 'Survey Mode'}</span>
          <span class="badge badge-amber">${currQ.difficulty}</span>
        </div>
        <p style="font-size: 0.88rem; color: var(--text-muted); margin-top: 4px;">
          Question ${qState.currentIdx + 1} of ${totalQ}
        </p>
      </div>

      <div style="display: flex; align-items: center; gap: 16px;">
        <div style="font-family: var(--font-mono); font-size: 1.15rem; font-weight: 700; color: var(--primary); background: #eef2ff; border: 1px solid #c7d2fe; padding: 6px 14px; border-radius: var(--radius-sm);" id="quiz-timer">
          ⏱️ ${timeStr}
        </div>
        <button class="btn btn-danger" id="btn-quiz-exit-top" style="padding: 8px 14px;">
          ✕ Exit Quiz
        </button>
      </div>
    </div>

    <!-- Stepper Navigation Pills -->
    <div class="quiz-stepper" id="quiz-stepper-container"></div>

    <!-- Question Box -->
    <div class="question-box">
      <div class="question-meta">
        <span class="question-topic">Topic: ${currQ.topic}</span>
        <span style="font-size: 0.82rem; color: var(--text-dim);">Pick one option</span>
      </div>

      <div class="question-text">
        ${currQ.question}
      </div>

      <!-- Option Cards -->
      <div class="options-grid" id="options-container"></div>

      <!-- Hint Accordion -->
      ${currQ.hint ? `
        <button class="hint-toggle" id="btn-toggle-hint">
          <span>💡 Need a hint?</span>
        </button>
        <div class="hint-box" id="hint-box-content">${currQ.hint}</div>
      ` : ''}
    </div>

    <!-- Bottom Controls -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
      <button class="btn btn-secondary" id="btn-prev-q" ${qState.currentIdx === 0 ? 'disabled style="opacity: 0.4;"' : ''}>
        ⬅ Previous
      </button>

      <div style="display: flex; gap: 12px;">
        ${qState.currentIdx < totalQ - 1 ? `
          <button class="btn btn-primary" id="btn-next-q">Next Question ➡</button>
        ` : `
          <button class="btn btn-primary" id="btn-submit-quiz" style="background: var(--accent-emerald);">
            Finish & Submit Quiz ✅
          </button>
        `}
      </div>
    </div>
  `;

  // Live Timer Interval
  if (!qState.timerInterval) {
    qState.timerInterval = setInterval(() => {
      const el = document.getElementById('quiz-timer');
      if (el) {
        const sec = Math.floor((Date.now() - qState.startTime) / 1000);
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        el.innerText = `⏱️ ${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
      }
    }, 1000);
  }

  // Render Stepper Pills
  const stepper = document.getElementById('quiz-stepper-container');
  for (let i = 0; i < totalQ; i++) {
    const pill = document.createElement('div');
    const isAnswered = Boolean(qState.answers[i]);
    const isCurrent = i === qState.currentIdx;

    pill.className = `step-pill ${isCurrent ? 'active' : ''} ${isAnswered ? 'answered' : ''}`;
    pill.innerText = isAnswered ? `${i + 1} ✓` : `${i + 1}`;
    pill.onclick = () => {
      sound.playClick();
      qState.currentIdx = i;
      renderCurrentView();
    };
    stepper.appendChild(pill);
  }

  // Render Option Cards
  const optionsGrid = document.getElementById('options-container');
  const opts = currQ.options;
  ['A', 'B', 'C', 'D'].forEach((letter) => {
    if (!opts[letter]) return;
    const isSelected = selectedAns === letter;
    const card = document.createElement('div');
    card.className = `option-card ${isSelected ? 'selected' : ''}`;
    card.innerHTML = `
      <div class="option-letter">${letter}</div>
      <div class="option-text">${opts[letter]}</div>
    `;

    card.onclick = () => {
      sound.playSelect();
      qState.answers[qState.currentIdx] = letter;
      renderCurrentView();
    };
    optionsGrid.appendChild(card);
  });

  // Hint Toggle
  const hintBtn = document.getElementById('btn-toggle-hint');
  const hintBox = document.getElementById('hint-box-content');
  if (hintBtn && hintBox) {
    hintBtn.onclick = () => {
      sound.playClick();
      hintBox.classList.toggle('open');
    };
  }

  // Navigation Buttons
  const prevBtn = document.getElementById('btn-prev-q');
  if (prevBtn && qState.currentIdx > 0) {
    prevBtn.onclick = () => {
      sound.playClick();
      qState.currentIdx--;
      renderCurrentView();
    };
  }

  const nextBtn = document.getElementById('btn-next-q');
  if (nextBtn) {
    nextBtn.onclick = () => {
      sound.playClick();
      qState.currentIdx++;
      renderCurrentView();
    };
  }

  const submitBtn = document.getElementById('btn-submit-quiz');
  if (submitBtn) {
    submitBtn.onclick = () => finishAndSubmitQuiz();
  }

  // Exit Quiz Handler
  const exitTop = document.getElementById('btn-quiz-exit-top');
  if (exitTop) {
    exitTop.onclick = () => {
      sound.playClick();
      document.getElementById('exit-modal').classList.add('open');
    };
  }
}

// Exit Quiz Modal Controls
document.getElementById('btn-modal-cancel').onclick = () => {
  sound.playClick();
  document.getElementById('exit-modal').classList.remove('open');
};

document.getElementById('btn-modal-confirm-exit').onclick = () => {
  sound.playClick();
  clearInterval(state.quiz.timerInterval);
  state.quiz.active = false;
  document.getElementById('exit-modal').classList.remove('open');
  showToast('Quiz exited. Your progress was not counted.', 'info');
  switchView('dashboard');
};

async function finishAndSubmitQuiz() {
  const qState = state.quiz;
  clearInterval(qState.timerInterval);

  const unanswered = [];
  for (let i = 0; i < qState.questions.length; i++) {
    if (!qState.answers[i]) unanswered.push(i + 1);
  }

  if (unanswered.length > 0) {
    const confirmSubmit = confirm(`You have unanswered questions: #${unanswered.join(', ')}. Submit anyway?`);
    if (!confirmSubmit) return;
  }

  showToast('Grading your responses...', 'info');

  try {
    const results = await api.submitQuiz(qState.sessionToken, state.user.id, qState.answers);
    state.lastResults = results;
    state.quiz.active = false;

    if (results.percentage >= 70) sound.playCelebrate();
    else sound.playTone(400, 'sine', 0.2, 0.08);

    switchView('results');
  } catch (err) {
    showToast('Failed to submit quiz: ' + err.message, 'error');
  }
}

// ==========================================================================
// 4. Session Results & Review View
// ==========================================================================
function renderResults(container) {
  const res = state.lastResults;
  if (!res) {
    container.innerHTML = `
      <div class="glass-card" style="text-align: center; padding: 60px 20px;">
        <h3>No recent results to show</h3>
        <p style="color: var(--text-muted); margin: 10px 0 20px 0;">Take a practice quiz to view your score and detailed review.</p>
        <button class="btn btn-primary" onclick="window.startNewQuizShortcut()">Go to Practice Quiz</button>
      </div>
    `;
    return;
  }

  const pct = res.percentage;
  const isGreat = pct >= 80;
  const isGood = pct >= 50;
  const statusTitle = isGreat ? 'Great Job! 🌟' : isGood ? 'Good Practice! Keep Going 👍' : 'Target Practice Identified 🎯';
  const badgeClass = isGreat ? 'badge-emerald' : isGood ? 'badge-amber' : 'badge-rose';

  container.innerHTML = `
    <!-- Celebration Card -->
    <div class="results-hero">
      <span class="badge ${badgeClass}" style="margin-bottom: 12px;">Quiz Complete</span>
      <h2 style="font-family: var(--font-heading); font-size: 2.2rem; font-weight: 800; color: #0f172a;">
        ${statusTitle}
      </h2>
      <div class="score-display">
        ${res.score} / ${res.total_questions}
      </div>
      <p style="color: var(--text-muted); font-size: 1.15rem; font-weight: 500;">
        ${pct}% Correct • Finished in ${Math.floor(res.elapsed_seconds / 60)}m ${Math.floor(res.elapsed_seconds % 60)}s
      </p>
    </div>

    <!-- Topic Breakdown & Improvement Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; margin-bottom: 28px;">
      
      <!-- Topic Table -->
      <div class="glass-card">
        <h3 style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 16px;">
          Topic Performance
        </h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 10px 8px;">Topic</th>
              <th style="padding: 10px 8px; text-align: center;">Questions</th>
              <th style="padding: 10px 8px; text-align: center;">Accuracy</th>
            </tr>
          </thead>
          <tbody>
            ${res.topic_breakdown.map((t) => `
              <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 12px 8px; font-weight: 500; color: #0f172a;">${t.topic_name}</td>
                <td style="padding: 12px 8px; text-align: center; color: var(--text-muted);">${t.correct}/${t.attempts}</td>
                <td style="padding: 12px 8px; text-align: center;">
                  <span class="badge ${t.accuracy >= 70 ? 'badge-emerald' : 'badge-rose'}">
                    ${Math.round(t.accuracy)}%
                  </span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <p style="font-size: 0.82rem; color: var(--text-dim); margin-top: 14px;">
          ℹ️ ${res.evaluation_note || 'Your skill level has been updated.'}
        </p>
      </div>

      <!-- Actionable Focus Card -->
      <div class="glass-card">
        <h3 style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 16px;">
          🎯 Recommended Practice Areas
        </h3>
        ${res.topics_to_practise && res.topics_to_practise.length > 0 ? `
          <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;">
            ${res.topics_to_practise.map((t) => `
              <div style="background: #fff1f2; border: 1px solid #fecdd3; border-radius: var(--radius-sm); padding: 12px 16px;">
                <div style="font-weight: 600; color: var(--accent-rose);">${t.topic_name}</div>
                <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">
                  Score: ${t.accuracy}% • ${t.reason}
                </div>
              </div>
            `).join('')}
          </div>
          <button class="btn btn-primary" id="btn-practice-weak-now" style="width: 100%;">
            🚀 Practice These Topics Now
          </button>
        ` : `
          <div style="text-align: center; padding: 30px 10px;">
            <div style="font-size: 2.2rem; margin-bottom: 10px;">🎉</div>
            <h4 style="color: var(--accent-emerald); font-weight: 700;">All Topics Cleared!</h4>
            <p style="font-size: 0.88rem; color: var(--text-muted); margin-top: 6px;">
              You achieved solid scores across all tested topics in this session!
            </p>
          </div>
        `}
      </div>
    </div>

    <!-- Question-by-Question Review -->
    <div class="glass-card">
      <h3 style="font-family: var(--font-heading); font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-bottom: 20px;">
        Question-by-Question Review & Explanations
      </h3>
      ${res.detailed_reviews.map((rev, idx) => `
        <div class="review-card ${rev.is_correct ? 'correct' : 'incorrect'}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="badge ${rev.is_correct ? 'badge-emerald' : 'badge-rose'}">
              ${rev.is_correct ? '✅ Correct' : '❌ Needs Review'}
            </span>
            <span class="badge badge-indigo">Question ${idx + 1} • ${rev.topic}</span>
          </div>

          <div style="font-size: 1.05rem; font-weight: 600; color: #0f172a; margin-bottom: 12px; line-height: 1.5;">
            ${rev.question}
          </div>

          <div style="font-size: 0.9rem; margin-bottom: 4px; color: #334155;">
            <strong>Your Choice:</strong> (${rev.selected_answer}) ${rev.selected_text || 'None'}
          </div>

          <div style="font-size: 0.9rem; color: var(--accent-emerald); margin-bottom: 10px;">
            <strong>Correct Answer:</strong> (${rev.correct_answer}) ${rev.correct_text}
          </div>

          <div class="review-explanation">
            <strong>💡 Helpful Explanation:</strong> ${rev.explanation}
          </div>
        </div>
      `).join('')}
    </div>
  `;

  const btnPractice = document.getElementById('btn-practice-weak-now');
  if (btnPractice) {
    btnPractice.onclick = () => {
      launchAdaptiveQuiz(res.subject_id, res.subject_name, null, 'adaptive');
    };
  }
}

window.startNewQuizShortcut = () => switchView('quiz');

// ==========================================================================
// 5. My Progress & History View
// ==========================================================================
async function renderAnalytics(container) {
  container.innerHTML = `
    <!-- Top Mastery Matrix -->
    <div class="glass-card" style="margin-bottom: 28px;">
      <h3 style="font-family: var(--font-heading); font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
        All Curriculum Skills
      </h3>
      <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 20px;">
        Your accuracy and progress status across all curriculum subjects and topics.
      </p>
      <div id="mastery-matrix-container" style="display: flex; flex-direction: column; gap: 20px;">
        <p style="color: var(--text-muted);">Loading skill progress...</p>
      </div>
    </div>

    <!-- Practice History Table -->
    <div class="glass-card">
      <h3 style="font-family: var(--font-heading); font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-bottom: 16px;">
        Previous Practice Quizzes
      </h3>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 12px 10px;">Quiz #</th>
              <th style="padding: 12px 10px;">Date</th>
              <th style="padding: 12px 10px;">Subject</th>
              <th style="padding: 12px 10px; text-align: center;">Score</th>
              <th style="padding: 12px 10px; text-align: center;">Accuracy</th>
              <th style="padding: 12px 10px;">Mode</th>
            </tr>
          </thead>
          <tbody id="history-table-body">
            <tr><td colspan="6" style="padding: 20px; text-align: center; color: var(--text-muted);">Loading past quizzes...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  try {
    // 1. Mastery Breakdown
    const masteryData = await api.getMastery(state.user.id);
    const matrixContainer = document.getElementById('mastery-matrix-container');
    matrixContainer.innerHTML = '';

    masteryData.forEach((subj) => {
      const subjBox = document.createElement('div');
      subjBox.style.background = '#f8fafc';
      subjBox.style.borderRadius = 'var(--radius-md)';
      subjBox.style.padding = '18px 20px';
      subjBox.style.border = '1px solid var(--border-subtle)';

      subjBox.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <h4 style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">${subj.subject_name}</h4>
          <span class="badge badge-indigo">${subj.topics.length} Topics</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
          ${subj.topics.map((t) => {
            const badgeCls = t.status === 'Mastered' ? 'badge-emerald' : t.status === 'Needs Practice' ? 'badge-rose' : 'badge-amber';
            return `
              <div style="background: #ffffff; padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">${t.topic_name}</span>
                  <span class="badge ${badgeCls}" style="font-size: 0.7rem;">${t.status}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                  <span>Score: ${Math.round(t.accuracy)}%</span>
                  <span>${t.attempts} questions</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
      matrixContainer.appendChild(subjBox);
    });

    // 2. Practice History
    const history = await api.getHistory(state.user.id);
    const tbody = document.getElementById('history-table-body');
    tbody.innerHTML = '';

    if (history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--text-muted);">No quizzes completed yet. Complete a quiz to view your history!</td></tr>';
      return;
    }

    history.forEach((h) => {
      const accuracy = h.total_questions > 0 ? Math.round((h.score / h.total_questions) * 100) : 0;
      const row = document.createElement('tr');
      row.style.borderBottom = '1px solid #f1f5f9';
      row.innerHTML = `
        <td style="padding: 12px 10px; font-family: var(--font-mono); font-weight: 600; color: var(--primary);">#${h.id}</td>
        <td style="padding: 12px 10px; color: var(--text-muted);">${h.created_at}</td>
        <td style="padding: 12px 10px; font-weight: 600; color: #0f172a;">${h.subject_name}</td>
        <td style="padding: 12px 10px; text-align: center; font-weight: 600;">${h.score} / ${h.total_questions}</td>
        <td style="padding: 12px 10px; text-align: center;">
          <span class="badge ${accuracy >= 70 ? 'badge-emerald' : 'badge-rose'}">${accuracy}%</span>
        </td>
        <td style="padding: 12px 10px;"><span class="badge badge-indigo">${h.mode === 'adaptive' ? 'Adaptive' : 'Survey'}</span></td>
      `;
      tbody.appendChild(row);
    });

  } catch (err) {
    showToast('Failed to load progress: ' + err.message, 'error');
  }
}

// ==========================================================================
// 6. AI Practice Lab (Interactive Simulator & Friendly Benchmarks)
// ==========================================================================
async function renderSimulator(container) {
  container.innerHTML = `
    <!-- Benchmark Header -->
    <div class="glass-card" style="margin-bottom: 28px;">
      <h3 style="font-family: var(--font-heading); font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
        AI Coach Performance & Benchmark
      </h3>
      <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 20px;">
        Evaluated on 18,000+ real student interactions to ensure accurate, calibrated practice recommendations.
      </p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;" id="benchmark-cards">
        <p style="color: var(--text-muted);">Loading model performance...</p>
      </div>
    </div>

    <!-- Live Interactive AI Simulator -->
    <div class="glass-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;">
        <div>
          <h3 style="font-family: var(--font-heading); font-size: 1.35rem; font-weight: 700; color: #0f172a;">
            Interactive Skill Simulator
          </h3>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-top: 4px;">
            Simulate answering questions! Click <strong>+ Correct</strong> or <strong>− Incorrect</strong> on any topic to see how the AI dynamically updates its prediction of your mastery in real time.
          </p>
        </div>
        <button class="btn btn-secondary" id="btn-reset-sim">🔄 Clear Sequence</button>
      </div>

      <!-- Action Chips for 15 Skills -->
      <div style="margin-bottom: 24px;">
        <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); display: block; margin-bottom: 10px;">
          Choose a topic to simulate an answer:
        </label>
        <div id="sim-skill-buttons" style="display: flex; flex-wrap: wrap; gap: 8px;"></div>
      </div>

      <!-- Simulated Steps History -->
      <div style="margin-bottom: 24px; background: #f8fafc; border-radius: var(--radius-md); padding: 14px; border: 1px solid var(--border-subtle);">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--text-muted); margin-bottom: 8px;">
          <span>Practice Steps Sequence (${state.simulatorSteps.length} trials)</span>
          <span id="sim-engine-label" class="badge badge-indigo">AI Neural Engine Active</span>
        </div>
        <div id="sim-steps-strip" style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px;">
          ${state.simulatorSteps.length === 0 ? '<span style="color: var(--text-dim); font-size: 0.85rem;">Click "+ Correct" or "− Incorrect" on any topic above to start!</span>' : ''}
        </div>
      </div>

      <!-- Live Probabilities Grid -->
      <h4 style="font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 14px;">
        Predicted Skill Mastery Level:
      </h4>
      <div id="sim-probability-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px;"></div>
    </div>
  `;

  // 1. Fetch Benchmark Data
  try {
    const bench = await api.getBenchmark();
    const bCards = document.getElementById('benchmark-cards');
    bCards.innerHTML = '';

    for (const [modelName, m] of Object.entries(bench.models)) {
      const card = document.createElement('div');
      card.style.background = '#f8fafc';
      card.style.border = '1px solid var(--border-subtle)';
      card.style.borderRadius = 'var(--radius-md)';
      card.style.padding = '18px';

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h4 style="font-weight: 700; font-size: 1.05rem; color: #0f172a;">${modelName}</h4>
          <span class="badge ${modelName.includes('DKT') ? 'badge-emerald' : 'badge-indigo'}">${m.type}</span>
        </div>
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Prediction Accuracy</div>
            <div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 700; color: var(--primary);">${m.test_accuracy}</div>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">ROC AUC</div>
            <div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 700; color: var(--accent-cyan);">${m.test_auc}</div>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Confidence Score</div>
            <div style="font-family: var(--font-mono); font-size: 1.25rem; font-weight: 700; color: var(--accent-emerald);">${m.test_ece}</div>
          </div>
        </div>
      `;
      bCards.appendChild(card);
    }

    // 2. Build Simulator Skills
    const skillContainer = document.getElementById('sim-skill-buttons');
    bench.available_skills.forEach((skillName) => {
      const chip = document.createElement('div');
      chip.style.display = 'inline-flex';
      chip.style.alignItems = 'center';
      chip.style.gap = '6px';
      chip.style.background = '#ffffff';
      chip.style.border = '1px solid var(--border-subtle)';
      chip.style.borderRadius = 'var(--radius-full)';
      chip.style.padding = '4px 8px 4px 12px';
      chip.style.boxShadow = 'var(--shadow-sm)';

      chip.innerHTML = `
        <span style="font-size: 0.82rem; font-weight: 500; color: #0f172a;">${skillName}</span>
        <button class="btn btn-secondary" style="padding: 2px 7px; font-size: 0.75rem; color: var(--accent-emerald);" title="Simulate Correct Answer">+ Correct</button>
        <button class="btn btn-secondary" style="padding: 2px 7px; font-size: 0.75rem; color: var(--accent-rose);" title="Simulate Incorrect Answer">− Miss</button>
      `;

      const [plusBtn, minusBtn] = chip.querySelectorAll('button');
      plusBtn.onclick = () => addSimStep(skillName, true);
      minusBtn.onclick = () => addSimStep(skillName, false);

      skillContainer.appendChild(chip);
    });

    document.getElementById('btn-reset-sim').onclick = () => {
      sound.playClick();
      state.simulatorSteps = [];
      updateSimulator();
    };

    updateSimulator();

  } catch (err) {
    showToast('Failed to load simulator: ' + err.message, 'error');
  }
}

async function addSimStep(topicName, isCorrect) {
  sound.playSelect();
  state.simulatorSteps.push({ topic_name: topicName, is_correct: isCorrect });
  updateSimulator();
}

async function updateSimulator() {
  const strip = document.getElementById('sim-steps-strip');
  const grid = document.getElementById('sim-probability-grid');
  if (!grid || !strip) return;

  // Render strip
  strip.innerHTML = state.simulatorSteps.length === 0
    ? '<span style="color: var(--text-dim); font-size: 0.85rem;">Click "+ Correct" or "− Miss" on any topic above to start!</span>'
    : state.simulatorSteps.map((s, idx) => `
        <span class="badge ${s.is_correct ? 'badge-emerald' : 'badge-rose'}" style="white-space: nowrap;">
          #${idx + 1} ${s.topic_name} ${s.is_correct ? '✓' : '✗'}
        </span>
      `).join('');

  // Call API simulate
  try {
    const res = await api.simulate(state.simulatorSteps);
    document.getElementById('sim-engine-label').innerText = res.model_used;

    grid.innerHTML = '';
    res.skills.forEach((s) => {
      const pct = Math.round(s.mastery_probability * 100);
      const isHigh = pct >= 75;
      const isMed = pct >= 50;
      const barColor = isHigh ? 'var(--accent-emerald)' : isMed ? 'var(--primary)' : 'var(--accent-rose)';

      const card = document.createElement('div');
      card.style.background = '#ffffff';
      card.style.border = '1px solid var(--border-subtle)';
      card.style.borderRadius = 'var(--radius-sm)';
      card.style.padding = '12px 14px';
      card.style.boxShadow = 'var(--shadow-sm)';

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-size: 0.85rem; font-weight: 600; color: #0f172a;">${s.topic_name}</span>
          <span style="font-family: var(--font-mono); font-size: 0.9rem; font-weight: 700; color: ${barColor};">${pct}%</span>
        </div>
        <div style="height: 6px; background: #f1f5f9; border-radius: var(--radius-full); overflow: hidden;">
          <div style="width: ${pct}%; height: 100%; background: ${barColor}; transition: width 0.3s ease;"></div>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    showToast('Simulation update failed: ' + err.message, 'error');
  }
}

// ==========================================================================
// 7. AI Study Coach View & WebSocket Streaming
// ==========================================================================
function formatMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks: ```python ... ```
  html = html.replace(/```(?:[a-zA-Z]*)\n([\s\S]*?)```/g, (match, code) => {
    return `<pre style="background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 8px; overflow-x: auto; font-family: var(--font-mono); font-size: 0.85rem; margin: 10px 0; border: 1px solid #1e293b;"><code>${code.trim()}</code></pre>`;
  });

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code style="background: #f1f5f9; color: #4f46e5; padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.88em; font-weight: 600;">$1</code>');

  // Headings: ### Heading
  html = html.replace(/^### (.*$)/gim, '<h4 style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 10px 0 6px;">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 12px 0 6px;">$1</h3>');

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #0f172a; font-weight: 700;">$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Horizontal rules
  html = html.replace(/^---$/gim, '<hr style="border: none; border-top: 1px solid #e2e8f0; margin: 12px 0;">');

  // Bullet points
  html = html.replace(/^[•\-\*] (.*$)/gim, '<li style="margin-left: 20px; margin-bottom: 4px; list-style-type: disc;">$1</li>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  // Clean up excessive <br> around block elements
  html = html.replace(/<br><(pre|h3|h4|hr|li)/g, '<$1');
  html = html.replace(/<\/(pre|h3|h4|hr|li)><br>/g, '</$1>');

  return html;
}

/**
 * Streams a tutor chat query via WebSocket with live chunks,
 * seamlessly falling back to REST if WebSocket disconnects.
 */
async function streamTutorChat(text, msgContainer, onComplete) {
  if (!text || !text.trim()) return;
  const cleanText = text.trim();

  // 1. User Message Bubble
  const uMsg = document.createElement('div');
  uMsg.className = 'msg-bubble msg-user';
  uMsg.innerText = cleanText;
  msgContainer.appendChild(uMsg);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  // 2. Tutor Placeholder Bubble with pulsing cursor
  const tMsg = document.createElement('div');
  tMsg.className = 'msg-bubble msg-tutor';
  tMsg.innerHTML = '<span class="tutor-stream-content"></span><span class="typing-cursor">▋</span>';
  msgContainer.appendChild(tMsg);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  const contentSpan = tMsg.querySelector('.tutor-stream-content');
  const cursorSpan = tMsg.querySelector('.typing-cursor');

  const studentName = state.user ? (state.user.display_name ? state.user.display_name.split(' ')[0] : state.user.username) : 'there';
  const studentId = state.user ? state.user.id : null;

  try {
    // Attempt WebSocket real-time streaming
    await tutorWS.streamMessage(
      {
        message: cleanText,
        username: studentName,
        student_id: studentId
      },
      {
        onStart: () => {
          contentSpan.innerText = '';
        },
        onChunk: (chunk) => {
          contentSpan.innerText += chunk;
          msgContainer.scrollTop = msgContainer.scrollHeight;
        },
        onDone: (finalReply) => {
          if (cursorSpan) cursorSpan.remove();
          tMsg.innerHTML = formatMarkdown(finalReply);
          msgContainer.scrollTop = msgContainer.scrollHeight;
          sound.playSelect();
          if (onComplete) onComplete(finalReply);
        }
      }
    );
  } catch (wsErr) {
    console.warn('[Tutor WS failed, using REST fallback]', wsErr);
    try {
      const res = await api.tutorChat(cleanText, null, null, studentId);
      if (cursorSpan) cursorSpan.remove();
      tMsg.innerHTML = formatMarkdown(res.reply);
      msgContainer.scrollTop = msgContainer.scrollHeight;
      sound.playSelect();
      if (onComplete) onComplete(res.reply);
    } catch (httpErr) {
      if (cursorSpan) cursorSpan.remove();
      tMsg.innerHTML = '<em>Sorry, I encountered an issue connecting. Please try again!</em>';
      showToast('Could not reach AI Study Coach', 'error');
    }
  }
}

function renderTutorView(container) {
  const firstName = state.user ? (state.user.display_name ? state.user.display_name.split(' ')[0] : 'there') : 'there';

  container.innerHTML = `
    <div style="max-width: 800px; margin: 0 auto;">
      <div class="glass-card" style="margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="brand-icon" style="width: 48px; height: 48px; font-size: 1.6rem;">🎓</div>
          <div>
            <h2 style="font-family: var(--font-heading); font-size: 1.6rem; font-weight: 700; color: #0f172a;">
              AI Study Coach
            </h2>
            <p style="font-size: 0.88rem; color: var(--text-muted);">
              Ask questions about any topic in plain English, get analogies, or prepare for upcoming quizzes.
            </p>
          </div>
        </div>
      </div>

      <!-- Embedded Chat Screen -->
      <div class="glass-card" style="height: 540px; display: flex; flex-direction: column;">
        <div id="tutor-full-messages" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; padding-bottom: 14px;">
          <div class="msg-bubble msg-tutor">
            Hey ${firstName}! 👋 I'm your AI Study Coach. What topic would you like to explore or practice today?
          </div>
        </div>

        <!-- Helpful Suggestion Chips -->
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
          <button class="btn btn-secondary prompt-chip" style="font-size: 0.78rem; padding: 4px 10px;">Explain Supervised vs Deep Learning</button>
          <button class="btn btn-secondary prompt-chip" style="font-size: 0.78rem; padding: 4px 10px;">How does Big O complexity work?</button>
          <button class="btn btn-secondary prompt-chip" style="font-size: 0.78rem; padding: 4px 10px;">Explain Dynamic Programming in simple terms</button>
        </div>

        <div style="display: flex; gap: 10px;">
          <input type="text" id="tutor-full-input" class="tutor-input" style="flex: 1;" placeholder="Type your question here (e.g. 'hi' or 'explain L1 vs L2')...">
          <button class="btn btn-primary" id="btn-tutor-full-send">Send</button>
        </div>
      </div>
    </div>
  `;

  const input = document.getElementById('tutor-full-input');
  const sendBtn = document.getElementById('btn-tutor-full-send');
  const msgBox = document.getElementById('tutor-full-messages');

  const onSend = () => {
    const text = input.value.trim();
    if (!text) return;
    sound.playClick();
    input.value = '';
    streamTutorChat(text, msgBox);
  };

  sendBtn.onclick = onSend;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') onSend();
  };

  document.querySelectorAll('.prompt-chip').forEach((chip) => {
    chip.onclick = () => {
      sound.playClick();
      streamTutorChat(chip.innerText, msgBox);
    };
  });
}

// Floating Tutor Drawer Event Handlers
const tutorFab = document.getElementById('btn-open-tutor');
const tutorPanel = document.getElementById('tutor-panel');
const tutorClose = document.getElementById('btn-close-tutor');
const tutorInput = document.getElementById('tutor-input-field');
const tutorSend = document.getElementById('btn-send-tutor');
const tutorMsgBox = document.getElementById('tutor-messages');

if (tutorFab && tutorPanel && tutorClose) {
  tutorFab.onclick = () => {
    sound.playClick();
    tutorPanel.classList.toggle('open');
    if (tutorPanel.classList.contains('open') && tutorInput) {
      setTimeout(() => tutorInput.focus(), 100);
    }
  };
  tutorClose.onclick = () => {
    sound.playClick();
    tutorPanel.classList.remove('open');
  };
}

if (tutorSend && tutorInput && tutorMsgBox) {
  const sendFloatingMsg = () => {
    const text = tutorInput.value.trim();
    if (!text) return;
    sound.playClick();
    tutorInput.value = '';
    streamTutorChat(text, tutorMsgBox);
  };

  tutorSend.onclick = sendFloatingMsg;
  tutorInput.onkeydown = (e) => {
    if (e.key === 'Enter') sendFloatingMsg();
  };
}

// ==========================================================================
// 8. Global Initialization
// ==========================================================================
function initApp() {
  initAmbientParticles('ambient-canvas');

  // Navigation Links
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.onclick = () => switchView(item.dataset.view);
  });

  // Topbar Start Quiz Button
  const topbarQuizBtn = document.getElementById('topbar-start-quiz-btn');
  if (topbarQuizBtn) {
    topbarQuizBtn.onclick = () => switchView('quiz');
  }

  // Audio Toggle Button
  const soundBtn = document.getElementById('btn-toggle-sound');
  const soundIcon = document.getElementById('sound-icon');
  const soundLabel = document.getElementById('sound-label');
  if (soundBtn) {
    soundBtn.onclick = () => {
      const isEnabled = sound.toggleSound();
      soundIcon.innerText = isEnabled ? '🔊' : '🔇';
      soundLabel.innerText = isEnabled ? 'Sound Effects: On' : 'Sound Effects: Muted';
      showToast(isEnabled ? 'Sound effects enabled' : 'Sound effects muted', 'info');
    };
  }

  // Sign Out Button
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.onclick = () => {
      sound.playClick();
      state.user = null;
      localStorage.removeItem('studymind_user');
      showToast('Signed out successfully', 'info');
      renderAuth();
    };
  }

  // Check saved session in LocalStorage
  const savedUser = localStorage.getItem('studymind_user');
  if (savedUser) {
    try {
      const userObj = JSON.parse(savedUser);
      setUserSession(userObj);
      return;
    } catch (e) {}
  }

  // Default to Auth screen
  renderAuth();
}

window.addEventListener('DOMContentLoaded', initApp);
