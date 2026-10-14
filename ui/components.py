"""
Reusable UI components and Plotly chart builders for StudyMind.
"""

from typing import List, Dict, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st


def render_hero_header(student_name: str, mode_label: str = "Student Portal") -> None:
    """Renders top header banner with branding and student info."""
    st.markdown(f"""
    <div class="hero-header">
        <div>
            <div class="brand-badge">Adaptive Learning Intelligence</div>
            <div style="font-family: 'Outfit', sans-serif; font-size: 1.8rem; font-weight: 700; color: #FFFFFF;">
                StudyMind
            </div>
            <div style="font-size: 0.88rem; color: #94A3B8; margin-top: 2px;">
                Personalized knowledge tracing & precision practice
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: #818CF8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                Logged in as
            </div>
            <div style="font-size: 1.15rem; font-weight: 600; color: #F8FAFC;">
                {student_name}
            </div>
            <div style="font-size: 0.78rem; color: #10B981;">
                ● Active Learning Session
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_grid(total_quizzes: int, avg_score: float, total_questions: int, topics_practiced: int) -> None:
    """Renders 4 modern metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Quizzes Completed</div>
            <div class="stat-value">{total_quizzes}</div>
            <div class="stat-sub"><span>🎯</span> Practice sessions</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        score_color = "#10B981" if avg_score >= 70 else ("#F59E0B" if avg_score >= 50 else "#F43F5E")
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Average Accuracy</div>
            <div class="stat-value" style="color: {score_color};">{avg_score:.1f}%</div>
            <div class="stat-sub"><span>📈</span> Cumulative performance</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Questions Solved</div>
            <div class="stat-value">{total_questions}</div>
            <div class="stat-sub"><span>📝</span> Verified responses</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Active Topics</div>
            <div class="stat-value">{topics_practiced}</div>
            <div class="stat-sub"><span>🧠</span> Curriculum coverage</div>
        </div>
        """, unsafe_allow_html=True)


def build_mastery_radar_chart(topic_stats: List[Dict[str, Any]]) -> go.Figure:
    """Builds interactive radar chart showing topic mastery percentages."""
    if not topic_stats:
        fig = go.Figure()
        fig.add_annotation(text="No topic practice data yet", showarrow=False, font=dict(color="#94A3B8", size=14))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    categories = [t["topic_name"] for t in topic_stats]
    accuracies = [t["accuracy"] for t in topic_stats]

    # Close the radar loop
    categories_closed = categories + [categories[0]]
    accuracies_closed = accuracies + [accuracies[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=accuracies_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.25)',
        line=dict(color='#818CF8', width=2),
        marker=dict(size=6, color='#6366F1'),
        name='Estimated Mastery'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=True,
                tickfont=dict(color="#94A3B8", size=10),
                gridcolor="rgba(255, 255, 255, 0.1)",
                linecolor="rgba(255, 255, 255, 0.1)"
            ),
            angularaxis=dict(
                tickfont=dict(color="#F8FAFC", size=11, family="Inter"),
                gridcolor="rgba(255, 255, 255, 0.1)",
                linecolor="rgba(255, 255, 255, 0.1)"
            ),
            bgcolor="rgba(17, 24, 39, 0.6)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=30),
        height=340,
        showlegend=False
    )
    return fig


def build_history_timeline_chart(history_records: List[Dict[str, Any]]) -> go.Figure:
    """Builds interactive score progress trajectory chart."""
    if not history_records:
        fig = go.Figure()
        fig.add_annotation(text="No quiz history available", showarrow=False, font=dict(color="#94A3B8", size=14))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    # Reverse chronologically so oldest is on left
    records = list(reversed(history_records))
    sessions = [f"Quiz #{i+1}" for i in range(len(records))]
    scores = [r["score"] for r in records]
    percentages = [round((r["score"] / r["total_questions"]) * 100, 1) for r in records]
    subjects = [r.get("subject_name", "") for r in records]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sessions,
        y=percentages,
        mode='lines+markers',
        line=dict(color='#06B6D4', width=3, shape='spline'),
        marker=dict(size=8, color='#38BDF8', line=dict(color='#FFFFFF', width=1.5)),
        fill='tozeroy',
        fillcolor='rgba(6, 182, 212, 0.12)',
        text=[f"Score: {s}/10 ({p}%)<br>Subject: {sub}" for s, p, sub in zip(scores, percentages, subjects)],
        hoverinfo='text',
        name='Quiz Score'
    ))

    # Add 70% proficiency benchmark reference line
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(16, 185, 129, 0.5)", 
                  annotation_text="Proficiency Target (70%)", annotation_position="bottom right",
                  annotation_font=dict(color="#10B981", size=10))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17, 24, 39, 0.5)",
        margin=dict(l=40, r=20, t=30, b=40),
        height=340,
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94A3B8", size=11),
            linecolor="rgba(255, 255, 255, 0.1)"
        ),
        yaxis=dict(
            range=[0, 105],
            gridcolor="rgba(255, 255, 255, 0.08)",
            tickfont=dict(color="#94A3B8", size=11),
            ticksuffix="%",
            linecolor="rgba(255, 255, 255, 0.1)"
        ),
        showlegend=False
    )
    return fig


def build_calibration_plot(calibration_dict: Dict[str, Any]) -> go.Figure:
    """Builds reliability curve comparing model confidence vs actual empirical accuracy."""
    fig = go.Figure()

    # Ideal diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode='lines',
        line=dict(color='rgba(255, 255, 255, 0.4)', dash='dash'),
        name='Perfect Calibration'
    ))

    colors = {
        "logistic_regression": "#818CF8",
        "random_forest": "#34D399",
        "dkt_gru": "#F472B6"
    }
    labels = {
        "logistic_regression": "Logistic Regression",
        "random_forest": "Random Forest",
        "dkt_gru": "Deep Knowledge Tracing (GRU)"
    }

    for key, data in calibration_dict.items():
        if not data or "bins" not in data:
            continue
        valid_bins = [b for b in data["bins"] if b["count"] > 0]
        if not valid_bins:
            continue
        confs = [b["confidence"] for b in valid_bins]
        accs = [b["accuracy"] for b in valid_bins]

        fig.add_trace(go.Scatter(
            x=confs, y=accs,
            mode='lines+markers',
            line=dict(color=colors.get(key, "#38BDF8"), width=2),
            marker=dict(size=7),
            name=f"{labels.get(key, key)} (ECE: {data.get('expected_calibration_error', 0):.3f})"
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17, 24, 39, 0.6)",
        xaxis=dict(
            title=dict(text="Predicted Probability (Confidence)", font=dict(color="#94A3B8")),
            range=[0, 1],
            gridcolor="rgba(255, 255, 255, 0.06)",
            tickfont=dict(color="#94A3B8")
        ),
        yaxis=dict(
            title=dict(text="Empirical Accuracy", font=dict(color="#94A3B8")),
            range=[0, 1],
            gridcolor="rgba(255, 255, 255, 0.06)",
            tickfont=dict(color="#94A3B8")
        ),
        legend=dict(
            font=dict(color="#F8FAFC", size=10),
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.1)"
        ),
        margin=dict(l=40, r=20, t=30, b=40),
        height=360
    )
    return fig
