# utils/visuals.py

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_timeline(df: pd.DataFrame):
    """Plot a timeline of alarms."""
    if df.empty or "Raise Date" not in df.columns or "Alarm Name" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title="No data available for timeline",
            xaxis_title="Date",
            yaxis_title="Events",
            template="plotly_white"
        )
        return fig

    fig = px.scatter(
        df,
        x="Raise Date",
        y="Alarm Name",
        color="Severity" if "Severity" in df.columns else None,
        hover_data=df.columns,
        title="Alarm Timeline"
    )
    fig.update_layout(template="plotly_white", xaxis_rangeslider_visible=True)
    return fig


def plot_counts(df: pd.DataFrame):
    """Plot top alarm counts."""
    if df.empty or "Alarm Name" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title="No data available for counts",
            xaxis_title="Alarm Name",
            yaxis_title="Count",
            template="plotly_white"
        )
        return fig

    counts = df["Alarm Name"].value_counts().reset_index()
    counts.columns = ["Alarm Name", "Count"]

    fig = px.bar(
        counts,
        x="Alarm Name",
        y="Count",
        title="Top Event Counts",
        text="Count"
    )
    fig.update_layout(template="plotly_white")
    return fig


def draw_root_cause_diagram(events_df: pd.DataFrame):
    """Draw a simple root cause diagram based on alarm/event sequences."""
    if events_df.empty or "Alarm Name" not in events_df.columns:
        fig = go.Figure()
        fig.update_layout(
            title="No data available for root cause diagram",
            template="plotly_white"
        )
        return fig

    # For demo: link events in sequence
    unique_alarms = events_df["Alarm Name"].unique()
    edges = [(unique_alarms[i], unique_alarms[i+1]) for i in range(len(unique_alarms)-1)]

    # Build a basic network diagram
    fig = go.Figure()
    for src, dst in edges:
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[unique_alarms.tolist().index(src), unique_alarms.tolist().index(dst)],
            mode="lines+markers+text",
            text=[src, dst],
            textposition="top center",
            line=dict(width=2, color="blue")
        ))

    fig.update_layout(
        title="Root Cause / Event Flow Diagram",
        showlegend=False,
        template="plotly_white"
    )
    return fig




