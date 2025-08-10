import streamlit as st
import pandas as pd
from pathlib import Path
from utils.parser import load_file, clean_events, generate_summary
from utils.visuals import plot_timeline, plot_counts, draw_root_cause_diagram

st.set_page_config(page_title="TSMC / Endpoint Log Analyzer — Multi-file Dashboard", layout="wide")

st.title("TSMC / Endpoint Log Analyzer — Multi-file Dashboard")

# File uploader
uploaded_files = st.file_uploader(
    "Upload log file(s) (txt, log). You may upload multiple files.",
    type=["txt", "log", "csv"],
    accept_multiple_files=True
)

# Load sample logs if none uploaded
if not uploaded_files:
    st.info("No files uploaded — loading sample logs for demo.")
    sample_dir = Path("sample_logs")
    uploaded_files = [open(f, "rb") for f in sample_dir.glob("*")]

# Parse logs
all_events = []
for file in uploaded_files:
    try:
        df = load_file(file)
        df["source_file"] = Path(file.name).name
        all_events.append(df)
    except Exception as e:
        st.error(f"Failed to parse {file.name}: {e}")

if all_events:
    df_all = pd.concat(all_events, ignore_index=True)
    cleaned_df = clean_events(df_all)

    # Sidebar filters
    st.sidebar.header("Filters")

    if "Raise Date" in cleaned_df.columns and pd.api.types.is_datetime64_any_dtype(cleaned_df["Raise Date"]):
        min_dt, max_dt = cleaned_df["Raise Date"].min(), cleaned_df["Raise Date"].max()
        date_range = st.sidebar.date_input("Date range (Raise Date)", [min_dt.date(), max_dt.date()])
        start_time = st.sidebar.time_input("Start time", value=pd.Timestamp("00:00").time())
        end_time = st.sidebar.time_input("End time", value=pd.Timestamp("23:59").time())
    else:
        date_range = None
        start_time = None
        end_time = None

    severities = cleaned_df["Severity"].dropna().unique().tolist() if "Severity" in cleaned_df.columns else []
    selected_severity = st.sidebar.multiselect("Severity", severities)

    alarm_filter = st.sidebar.text_input("Alarm name/code filter (partial)")
    keyword_filter = st.sidebar.text_input("Full-text search")

    source_files = cleaned_df["source_file"].dropna().unique().tolist()
    selected_files = st.sidebar.multiselect("Choose source file(s)", source_files, default=source_files)

    # Apply filters
    df_filtered = cleaned_df.copy()

    if date_range and "Raise Date" in df_filtered.columns:
        start_dt = pd.to_datetime(str(date_range[0]) + " " + str(start_time))
        end_dt = pd.to_datetime(str(date_range[1]) + " " + str(end_time))
        df_filtered = df_filtered[(df_filtered["Raise Date"] >= start_dt) & (df_filtered["Raise Date"] <= end_dt)]

    if selected_severity:
        df_filtered = df_filtered[df_filtered["Severity"].isin(selected_severity)]

    if alarm_filter and "Alarm Name" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Alarm Name"].str.contains(alarm_filter, case=False, na=False)]

    if keyword_filter:
        df_filtered = df_filtered[df_filtered.apply(lambda row: row.astype(str).str.contains(keyword_filter, case=False, na=False).any(), axis=1)]

    if selected_files:
        df_filtered = df_filtered[df_filtered["source_file"].isin(selected_files)]

    # Summary KPIs
    st.subheader("Summary of parsed files")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Files processed", len(selected_files))
    col2.metric("Total parsed events", len(df_filtered))
    col3.metric("Critical / Error events", len(df_filtered[df_filtered["Severity"].str.lower().isin(["critical", "error"])] if "Severity" in df_filtered.columns else []))
    col4.metric("Unique alarms", df_filtered["Alarm Name"].nunique() if "Alarm Name" in df_filtered.columns else 0)

    # Charts
    st.subheader("Alarm timeline")
    st.plotly_chart(plot_timeline(df_filtered), use_container_width=True)

    st.subheader("Top event counts")
    st.plotly_chart(plot_counts(df_filtered), use_container_width=True)

    # Root cause diagram
    st.subheader("Root cause / Flow diagrams (per-file)")
    file_for_diagram = st.selectbox("Select file", selected_files)
    if file_for_diagram:
        st.image(draw_root_cause_diagram(df_filtered[df_filtered["source_file"] == file_for_diagram]), use_container_width=True)

    # Event details table
    st.subheader("Event Details Table")
    EXPECTED_COLS = ["Device Name", "Alarm Name", "Severity", "Status", "Raise Date", "Terminated Date", "Message", "source_file"]
    for col in EXPECTED_COLS:
        if col not in df_filtered.columns:
            df_filtered[col] = None
    if "Raise Date" in df_filtered.columns:
        df_filtered = df_filtered.sort_values("Raise Date", na_position="last")
    st.dataframe(df_filtered[EXPECTED_COLS], height=350, use_container_width=True)

    # Download button
    st.download_button("Download filtered events as CSV", df_filtered.to_csv(index=False), "filtered_events.csv", "text/csv")
else:
    st.warning("No valid log data parsed.")



