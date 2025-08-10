import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import io

def plot_counts(df):
    """Bar chart of top alarms or severities."""
    if "Alarm Name" in df.columns and not df.empty:
        counts = df["Alarm Name"].value_counts().reset_index()
        counts.columns = ["Alarm Name", "Count"]
        return px.bar(counts, x="Alarm Name", y="Count", title="Top Event Counts")
    elif "Severity" in df.columns and not df.empty:
        counts = df["Severity"].value_counts().reset_index()
        counts.columns = ["Severity", "Count"]
        return px.bar(counts, x="Severity", y="Count", title="Top Severity Counts")
    else:
        return px.bar(title="No Data to Display")

def plot_timeline_altair(df):
    """Timeline scatter plot for events."""
    if "Raise Date" not in df.columns or df.empty:
        return px.scatter(title="No timeline data")
    try:
        fig = px.scatter(
            df,
            x="Raise Date",
            y="Alarm Name" if "Alarm Name" in df.columns else "Message",
            color="Severity" if "Severity" in df.columns else None,
            title="Alarm Timeline",
            hover_data=df.columns
        )
        return fig
    except Exception as e:
        return px.scatter(title=f"Timeline error: {e}")

def draw_root_cause_diagram(df):
    """Generate a root cause diagram or a fallback sequential flow diagram."""
    if df.empty:
        return _fallback_image(["Log Start", "No events parsed", "Log End"])

    # Prefer Alarm Name, otherwise Message
    if "Alarm Name" in df.columns and df["Alarm Name"].notna().any():
        events = df["Alarm Name"].dropna().astype(str).unique().tolist()
    elif "Message" in df.columns and df["Message"].notna().any():
        events = df["Message"].dropna().astype(str).unique().tolist()
    else:
        events = []

    # If we still have no events
    if not events:
        events = ["Log Start", "Log End"]

    # Limit number of events in diagram for readability
    if len(events) > 12:
        events = events[:5] + ["..."] + events[-5:]

    return _fallback_image(events)

def _fallback_image(steps):
    """Draw a very simple left-to-right flow diagram using Pillow."""
    width, height = 200 * len(steps), 200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    for i, step in enumerate(steps):
        x = i * 200 + 50
        y = height // 2
        draw.ellipse((x - 30, y - 30, x + 30, y + 30), fill="lightblue", outline="black")
        text_w, text_h = draw.textsize(step, font=font)
        draw.text((x - text_w // 2, y - text_h // 2), step, fill="black", font=font)
        if i < len(steps) - 1:
            draw.line((x + 30, y, x + 170, y), fill="black", width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf



