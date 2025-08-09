import plotly.express as px
import matplotlib.pyplot as plt
import networkx as nx

def plot_timeline(df):
    if "Raise Date" in df.columns and "Alarm Name" in df.columns:
        fig = px.scatter(df, x="Raise Date", y="Alarm Name", color="Severity", hover_data=df.columns)
        return fig
    return px.scatter()

def plot_counts(df):
    if "Raise Date" in df.columns:
        fig = px.histogram(df, x="Raise Date", color="Alarm Name", nbins=20)
        return fig
    return px.histogram()

def draw_root_cause_diagram(df):
    G = nx.Graph()
    if "Alarm Name" in df.columns and "Device Name" in df.columns:
        for _, row in df.iterrows():
            G.add_edge(row["Device Name"], row["Alarm Name"])
    plt.figure(figsize=(8,6))
    nx.draw(G, with_labels=True, node_color="skyblue", node_size=1500, font_size=8)
    return plt
    
