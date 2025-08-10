# utils/visuals.py
import pandas as pd
import plotly.express as px
import altair as alt
from PIL import Image, ImageDraw, ImageFont


def plot_timeline_altair(df: pd.DataFrame):
    """Plot alarm/event timeline using Altair."""
    if df.empty:
        return alt.Chart(pd.DataFrame({"No data": []})).mark_text(text="No data").encode()
    if "Raise Date" not in df.columns:
        return alt.Chart(pd.DataFrame({"No data": []})).mark_text(text="Missing Raise Date").encode()

    chart = (
        alt.Chart(df)
        .mark_circle(size=60)
        .encode(
            x="Raise Date:T",
            y=alt.Y("Alarm Name:N", sort="-x"),
            color="Severity:N",
            tooltip=["Device Name", "Alarm Name", "Severity", "Raise Date", "Terminated Date", "Message", "source_file"],
        )
        .interactive()
    )
    return chart


def plot_counts(df: pd.DataFrame):
    """Plot histogram of event/alarm counts."""
    if df.empty or "Alarm Name" not in df.columns:
        return px.histogram(title="No data")
    fig = px.histogram(
        df,
        x="Alarm Name",
        color="Severity" if "Severity" in df.columns else None,
        title="Alarm/Event Counts",
    )
    fig.update_xaxes(categoryorder="total descending")
    return fig


def draw_root_cause_diagram(df: pd.DataFrame):
    """Draw a root cause / flow diagram from log events."""
    width, height = 900, 600
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    if df.empty:
        draw.text((10, 10), "No events found in file", fill="black", font=font)
        return img

    # Use Raise Date for sorting
    if "Raise Date" in df.columns:
        df_sorted = df.sort_values("Raise Date")
    else:
        df_sorted = df.copy()

    # Always make a flow, even for unknown alarms
    steps = []
    for _, row in df_sorted.iterrows():
        label_parts = []
        if "Alarm Name" in row and pd.notna(row["Alarm Name"]):
            label_parts.append(str(row["Alarm Name"]))
        if "Severity" in row and pd.notna(row["Severity"]):
            label_parts.append(f"({row['Severity']})")
        if "Raise Date" in row and pd.notna(row["Raise Date"]):
            label_parts.append(str(row["Raise Date"]))
        steps.append(" ".join(label_parts) if label_parts else "Event")

    if not steps:
        steps = ["Log start", "Log end"]

    # Layout vertically
    y = 40
    for i, step in enumerate(steps):
        draw.rectangle([50, y - 10, width - 50, y + 20], outline="black", width=1)
        draw.text((60, y), step, fill="black", font=font)
        if i < len(steps) - 1:
            draw.line([width // 2, y + 20, width // 2, y + 50], fill="gray", width=2)
        y += 60
        if y > height - 40:
            break

    return img


# Keep backward compatibility with app.py
plot_timeline = plot_timeline_altair




