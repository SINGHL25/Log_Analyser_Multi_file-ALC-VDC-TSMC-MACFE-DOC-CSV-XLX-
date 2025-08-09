import streamlit as st
import pandas as pd
import io
from utils.parser import load_file, clean_events, generate_summary
from utils.visuals import plot_timeline, plot_counts, draw_root_cause_diagram

st.set_page_config(page_title="Universal Log & Event Analyzer", layout="wide")
st.title("📊 Universal Log & Event Analyzer")
st.markdown("Upload CSV, Excel, JSON, TXT, PDF, or Word files for automated parsing, filtering, and summary.")

uploaded_files = st.file_uploader(
    "Upload your log or data files",
    type=["csv", "xls", "xlsx", "json", "txt", "pdf", "docx"],
    accept_multiple_files=True
)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        try:
            df = load_file(file)
            if df is not None and not df.empty:
                df["source_file"] = file.name
                dfs.append(df)
        except Exception as e:
            st.error(f"Error parsing {file.name}: {e}")

    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        cleaned_df, dropped = clean_events(combined_df)

        # Sidebar filters
        st.sidebar.header("Filters")
        if "Raise Date" in cleaned_df.columns:
            date_min = pd.to_datetime(cleaned_df["Raise Date"], errors='coerce').min()
            date_max = pd.to_datetime(cleaned_df["Raise Date"], errors='coerce').max()
            date_range = st.sidebar.date_input("Date range", [date_min, date_max])
            if len(date_range) == 2:
                cleaned_df = cleaned_df[
                    (pd.to_datetime(cleaned_df["Raise Date"], errors='coerce') >= pd.to_datetime(date_range[0])) &
                    (pd.to_datetime(cleaned_df["Raise Date"], errors='coerce') <= pd.to_datetime(date_range[1]))
                ]

        if "Severity" in cleaned_df.columns:
            severity_options = st.sidebar.multiselect(
                "Severity", options=cleaned_df["Severity"].dropna().unique(),
                default=list(cleaned_df["Severity"].dropna().unique())
            )
            if severity_options:
                cleaned_df = cleaned_df[cleaned_df["Severity"].isin(severity_options)]

        # Summary
        st.subheader("📄 Executive Summary")
        summary_text = generate_summary(cleaned_df)
        st.markdown(f"```text\n{summary_text}\n```")

        # Event Table
        st.subheader("📋 Event Details")
        st.dataframe(cleaned_df, use_container_width=True)

        # Download
        excel_buffer = io.BytesIO()
        cleaned_df.to_excel(excel_buffer, index=False)
        st.download_button("Download as Excel", data=excel_buffer, file_name="events_cleaned.xlsx")

        # Visuals
        st.subheader("📈 Visualizations")
        st.plotly_chart(plot_timeline(cleaned_df), use_container_width=True)
        st.plotly_chart(plot_counts(cleaned_df), use_container_width=True)
        st.pyplot(draw_root_cause_diagram(cleaned_df))

    else:
        st.warning("No valid data parsed from uploaded files.")

