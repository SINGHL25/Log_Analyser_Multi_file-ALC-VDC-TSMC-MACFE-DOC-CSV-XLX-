import plotly.express as px
import pandas as pd
from PIL import Image, ImageDraw

def plot_timeline(df):
    if df.empty or "Raise Date" not in df.columns:
        return px.scatter(title="No timeline data")
    df_plot = df.dropna(subset=["Raise Date"])
    if df_plot.empty:
        return px.scatter(title="No valid Raise Date values")
    return px.scatter(df_plot, x="Raise Date", y="Alarm Name", color="Severity", hover_data=["Message", "source_file"])

def plot_counts(df):
    if df.empty or "Alarm Name" not in df.columns:
        return px.bar(title="No alarm count data")
    return px.histogram(df, x="Alarm Name", color="Severity")

def draw_root_cause_diagram(df):
    """
    Dummy diagram generator — replace with your RCA logic.
    """
    img = Image.new("RGB", (800, 400), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 10), f"Root Cause Diagram for {df['source_file'].iloc[0] if not df.empty else 'N/A'}", fill=(0, 0, 0))
    return img



