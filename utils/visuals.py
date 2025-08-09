import pandas as pd
import plotly.express as px
from PIL import Image, ImageDraw


# Plot alarm/event counts
def plot_counts(df):
    if df.empty:
        return px.histogram(pd.DataFrame({"No data": []}), x="No data", title="No events to plot")

    if "Alarm Name" in df.columns:
        x_col = "Alarm Name"
    elif "Severity" in df.columns:
        x_col = "Severity"
    else:
        x_col = df.columns[0]  # fallback

    return px.histogram(
        df,
        x=x_col,
        title=f"Event Counts by {x_col}",
        text_auto=True
    )


# Timeline plot (Plotly version for app.py compatibility)
def plot_timeline(df):
    if df.empty or "Raise Date" not in df.columns:
        return px.scatter(pd.DataFrame({"No data": []}), x="No data", y="No data", title="No timeline data")

    df_t = df.copy()
    df_t["Raise Date"] = pd.to_datetime(df_t["Raise Date"], errors="coerce")
    df_t = df_t.dropna(subset=["Raise Date"])

    if df_t.empty:
        return px.scatter(pd.DataFrame({"No data": []}), x="No data", y="No data", title="No timeline data")

    y_col = "Alarm Name" if "Alarm Name" in df_t.columns else df_t.columns[0]
    color_col = "Severity" if "Severity" in df_t.columns else None

    fig = px.scatter(
        df_t,
        x="Raise Date",
        y=y_col,
        color=color_col,
        title="Event Timeline",
        hover_data=list(df_t.columns)
    )

    return fig


# Root cause diagram placeholder
def draw_root_cause_diagram(events):
    img = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(img)

    if not events:
        draw.text((10, 10), "No events to display", fill="black")
        return img

    draw.text((10, 10), "Root Cause Diagram", fill="black")
    y = 50
    for event in events[:10]:  # limit to 10
        draw.text((10, y), str(event), fill="blue")
        y += 20

    return img



# --- Backward compatibility aliases for app.py ---
plot_timeline = plot_timeline_altair
draw_root_cause_diagram = draw_root_cause_diagram_pil

