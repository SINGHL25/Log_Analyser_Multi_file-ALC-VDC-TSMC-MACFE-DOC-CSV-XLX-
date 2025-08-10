# utils/visuals.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont


def plot_timeline(df: pd.DataFrame):
    """Plot a timeline of alarms as a Plotly scatter chart."""
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
    """Plot a bar chart of top alarm counts."""
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


def draw_root_cause_diagram(df: pd.DataFrame):
    """
    Creates a simple root cause diagram from events in a DataFrame.
    Always returns a PIL image so Streamlit st.image() won't break.
    """
    img_width, img_height = 900, 600
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    if df.empty:
        draw.text((20, 20), "No events found for this file.", fill="black", font=font)
        return img

    events = df["Alarm Name"].unique().tolist() if "Alarm Name" in df.columns else []
    if not events:
        draw.text((20, 20), "No Alarm Name data found.", fill="black", font=font)
        return img

    draw.text((20, 20), "Root Cause Diagram", fill="black", font=font)

    box_width, box_height = 250, 40
    x_start, y_start = 50, 80
    y_gap = 70

    for i, event in enumerate(events):
        top_left = (x_start, y_start + i * y_gap)
        bottom_right = (x_start + box_width, y_start + box_height + i * y_gap)
        draw.rectangle([top_left, bottom_right], outline="black", width=2)
        draw.text((top_left[0] + 5, top_left[1] + 10), str(event), fill="black", font=font)

        if i < len(events) - 1:
            arrow_start = (x_start + box_width, y_start + box_height // 2 + i * y_gap)
            arrow_end = (x_start + box_width + 50, y_start + box_height // 2 + i * y_gap)
            draw.line([arrow_start, arrow_end], fill="black", width=2)
            draw.polygon([
                (arrow_end[0], arrow_end[1]),
                (arrow_end[0] - 10, arrow_end[1] - 5),
                (arrow_end[0] - 10, arrow_end[1] + 5)
            ], fill="black")

    return img





