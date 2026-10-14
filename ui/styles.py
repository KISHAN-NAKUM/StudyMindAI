"""
Design system and CSS stylesheets for StudyMind.
Implements a state-of-the-art dark glassmorphic academic aesthetic with
vibrant gradients, modern typography, and refined micro-interactions.
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

:root {
    --bg-primary: #0B0F19;
    --bg-card: rgba(17, 24, 39, 0.75);
    --bg-card-hover: rgba(30, 41, 59, 0.85);
    --border-card: rgba(99, 102, 241, 0.2);
    --border-glow: rgba(129, 140, 248, 0.4);
    --primary-indigo: #6366F1;
    --primary-violet: #8B5CF6;
    --accent-cyan: #06B6D4;
    --accent-emerald: #10B981;
    --accent-amber: #F59E0B;
    --accent-rose: #F43F5E;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
}

/* Base Body Styles */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
}

h1, h2, h3, h4, .brand-title {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
}

/* Hero Header Component */
.hero-header {
    background: linear-gradient(135deg, rgba(30, 27, 75, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 0 15px rgba(99, 102, 241, 0.15);
    display: flex;
    justify-content: space-between;
    align-items: center;
    backdrop-filter: blur(12px);
}

.brand-badge {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: #FFFFFF;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 4px 12px;
    border-radius: 9999px;
    display: inline-block;
    margin-bottom: 8px;
    box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);
}

/* Glassmorphic Cards */
.study-card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
    backdrop-filter: blur(10px);
    transition: all 0.25s ease-in-out;
}

.study-card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 8px 24px -4px rgba(99, 102, 241, 0.15);
}

/* KPI Stat Cards */
.stat-card {
    background: linear-gradient(145deg, rgba(17, 24, 39, 0.9), rgba(15, 23, 42, 0.8));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 18px 20px;
    text-align: left;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.35);
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, var(--primary-indigo), var(--accent-cyan));
}

.stat-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.stat-value {
    font-family: 'Outfit', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.1;
}

.stat-sub {
    font-size: 0.75rem;
    color: var(--accent-emerald);
    margin-top: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
}

/* Badges & Tags */
.pill-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.pill-indigo {
    background: rgba(99, 102, 241, 0.15);
    color: #A5B4FC;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.pill-emerald {
    background: rgba(16, 185, 129, 0.15);
    color: #6EE7B7;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.pill-amber {
    background: rgba(245, 158, 11, 0.15);
    color: #FCD34D;
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.pill-rose {
    background: rgba(244, 63, 94, 0.15);
    color: #FDA4AF;
    border: 1px solid rgba(244, 63, 94, 0.3);
}

/* Question Taking Interface */
.question-container {
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 16px;
    padding: 28px;
    margin-top: 16px;
    box-shadow: 0 12px 30px -10px rgba(0, 0, 0, 0.5);
}

.question-text {
    font-family: 'Outfit', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: #FFFFFF;
    line-height: 1.5;
    margin-bottom: 20px;
}

/* Streamlit Button Enhancements */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
}

/* Question Review Cards */
.review-card-correct {
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-left: 4px solid #10B981;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
}

.review-card-incorrect {
    background: rgba(244, 63, 94, 0.05);
    border: 1px solid rgba(244, 63, 94, 0.3);
    border-left: 4px solid #F43F5E;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
}

/* Custom Navigation Tabs styling */
.nav-pill {
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 600;
    color: var(--text-secondary);
    background: transparent;
    cursor: pointer;
    text-align: center;
}

.nav-pill-active {
    color: #FFFFFF;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(139, 92, 246, 0.4));
    border: 1px solid var(--border-glow);
}
</style>
"""


def apply_custom_styles():
    """Returns CSS markdown string to inject into Streamlit app."""
    return CUSTOM_CSS
