import plotly.express as px
import pandas as pd
import altair as alt

# Plot alarm/event counts
def plot_counts(df):
    if df.empty:
        return px.histogram(pd.DataFrame({"No data": []}), x="No data", title="No events to plot")

    if "Alarm Name" in df.columns:
        x_col = "Alarm Name"
    elif "Severity" in df.columns:
        x_col = "Severity"
    else:
        x_col = df.columns[0]  # fallback to first column

    return px.histogram(
        df,
        x=x_col,
        title=f"Event Counts by {x_col}",
        text_auto=True
    )


# Timeline plot
def plot_timeline_altair(df):
    if df.empty or "Raise Date" not in df.columns:
        return alt.Chart(pd.DataFrame({"No timeline data": []})).mark_text(text="No timeline data")

    df_t = df.copy()
    df_t["Raise Date"] = pd.to_datetime(df_t["Raise Date"], errors="coerce")
    df_t = df_t.dropna(subset=["Raise Date"])

    if df_t.empty:
        return alt.Chart(pd.DataFrame({"No timeline data": []})).mark_text(text="No timeline data")

    x_col = "Raise Date"
    color_col = "Severity" if "Severity" in df_t.columns else None

    chart = alt.Chart(df_t).mark_circle(size=60).encode(
        x=x_col,
        y=alt.Y("Alarm Name", sort=None) if "Alarm Name" in df_t.columns else alt.Y("index", sort=None),
        color=color_col if color_col else alt.value("blue"),
        tooltip=list(df_t.columns)
    ).properties(title="Event Timeline", width=700, height=400)

    return chart


# Root cause diagram placeholder (still functional if no data)
def draw_root_cause_diagram_pil(events):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(img)

    if not events:
        draw.text((10, 10), "No events to display", fill="black")
        return img

    draw.text((10, 10), "Root Cause Diagram", fill="black")

    y = 50
    for event in events[:10]:  # limit to 10 events for diagram
        draw.text((10, y), str(event), fill="blue")
        y += 20

    return img


# --- Backward compatibility aliases for app.py ---
plot_timeline = plot_timeline_altair
draw_root_cause_diagram = draw_root_cause_diagram_pil

