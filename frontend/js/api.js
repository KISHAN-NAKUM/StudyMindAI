/**
 * StudyMindAI REST & WebSocket API Client
 * Clean asynchronous client communicating with FastAPI backend.
 */

const API_BASE = window.location.origin;

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errJson = await response.json();
        errorMsg = errJson.detail || errJson.message || errorMsg;
      } catch (e) {}
      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

// WebSocket connection singleton for real-time AI tutor
class TutorWebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = new Set();
    this.connecting = false;
  }

  getWsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/tutor/ws`;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve(this.ws);
    }
    if (this.connecting && this.ws) {
      return new Promise((resolve, reject) => {
        const checkInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            clearInterval(checkInterval);
            resolve(this.ws);
          } else if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
            clearInterval(checkInterval);
            reject(new Error('WebSocket connection closed'));
          }
        }, 50);
      });
    }

    this.connecting = true;
    return new Promise((resolve, reject) => {
      try {
        const url = this.getWsUrl();
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          this.connecting = false;
          resolve(this.ws);
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.listeners.forEach((listener) => {
              try { listener(data); } catch (e) { console.error(e); }
            });
          } catch (e) {
            console.error('[WS Parse Error]', e);
          }
        };

        this.ws.onerror = (err) => {
          this.connecting = false;
          reject(err);
        };

        this.ws.onclose = () => {
          this.connecting = false;
          this.ws = null;
        };
      } catch (e) {
        this.connecting = false;
        reject(e);
      }
    });
  }

  async send(payload) {
    await this.connect();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    } else {
      throw new Error('WebSocket connection not open');
    }
  }

  /**
   * Streams a message from the WebSocket with live callbacks.
   */
  async streamMessage(payload, callbacks = {}) {
    await this.connect();
    const { onStart, onChunk, onDone, onError } = callbacks;

    return new Promise((resolve, reject) => {
      let accumulated = '';
      const removeListener = this.addListener((data) => {
        if (data.type === 'start') {
          if (onStart) onStart();
        } else if (data.type === 'chunk') {
          accumulated += data.content;
          if (onChunk) onChunk(data.content, accumulated);
        } else if (data.type === 'done') {
          removeListener();
          const finalReply = data.reply || accumulated;
          if (onDone) onDone(finalReply);
          resolve(finalReply);
        } else if (data.type === 'error') {
          removeListener();
          const err = new Error(data.message || 'WebSocket streaming error');
          if (onError) onError(err);
          reject(err);
        }
      });

      try {
        this.ws.send(JSON.stringify(payload));
      } catch (err) {
        removeListener();
        if (onError) onError(err);
        reject(err);
      }
    });
  }

  addListener(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
}

export const tutorWS = new TutorWebSocketManager();

export const api = {
  // Auth
  login: (username, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    }),

  demoLogin: () =>
    request('/api/auth/demo', {
      method: 'POST'
    }),

  register: (username, displayName, password) =>
    request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, display_name: displayName, password })
    }),

  getStudent: (studentId) => request(`/api/auth/me/${studentId}`),

  // Subjects
  getSubjects: () => request('/api/subjects'),
  getTopics: (subjectId) => request(`/api/subjects/${subjectId}/topics`),

  // Quiz
  generateQuiz: (payload) =>
    request('/api/quiz/generate', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),

  submitQuiz: (sessionToken, studentId, answers) =>
    request('/api/quiz/submit', {
      method: 'POST',
      body: JSON.stringify({ session_token: sessionToken, student_id: studentId, answers })
    }),

  getHistory: (studentId) => request(`/api/quiz/history/${studentId}`),
  getSessionDetails: (sessionId, studentId) =>
    request(`/api/quiz/session/${sessionId}?student_id=${studentId}`),

  // Analytics
  getOverview: (studentId) => request(`/api/analytics/overview/${studentId}`),
  getMastery: (studentId, subjectId) => {
    const query = subjectId ? `?subject_id=${subjectId}` : '';
    return request(`/api/analytics/mastery/${studentId}${query}`);
  },
  getTimeline: (studentId) => request(`/api/analytics/timeline/${studentId}`),

  // ML & Simulator
  getBenchmark: () => request('/api/ml/benchmark'),
  simulate: (steps) =>
    request('/api/ml/simulate', {
      method: 'POST',
      body: JSON.stringify({ steps })
    }),

  // AI Tutor (REST fallback)
  tutorChat: (message, topic = null, subject = null, studentId = null) =>
    request('/api/tutor/chat', {
      method: 'POST',
      body: JSON.stringify({ message, topic, subject, student_id: studentId })
    })
};
