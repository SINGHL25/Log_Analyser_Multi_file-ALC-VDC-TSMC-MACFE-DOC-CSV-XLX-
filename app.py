"""
Universal Log & Event Analyzer (single-file Streamlit app)
Supports: TSMC-like logs, McScript/McAfee logs, VDC logs (heuristics from session).
Drop multiple text/log files, filter, visualize, download Excel.
"""

import re
import io
from datetime import datetime, time
from typing import List, Dict, Optional, Tuple

import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image, ImageDraw
from dateutil import parser as dparser


# ------------------------
# Parsing utilities
# ------------------------
# Recognize several timestamp formats found in the logs:
TSMC_EMBED_TS = re.compile(r'/(\d{8})/(\d{2}:\d{2}:\d{2}(?:\.\d+)?)')  # :)/20250731/22:40:10.619000/
ISO_TS = re.compile(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)')  # 2025-07-31 22:37:42
ISO_TS_NO_SEP = re.compile(r'(\d{8}-\d{2}:\d{2}:\d{2})')  # sometimes 20250808-00:00:29
VDC_TS = re.compile(r':\)/(\d{4})(\d{2})(\d{2})/(\d{2}:\d{2}:\d{2}\.\d+)')  # :)/20250808/00:00:02.227331/

# Patterns to find alarms and important events
ALARM_RAISED_PAT = re.compile(r'Alarm\s+([0-9A-Fa-f]{3,4})\s+has\s+been\s+raised|/W/Alarm\s+([0-9A-Fa-f]{3,4})\s+has\s+been\s+raised', re.IGNORECASE)
ALARM_TERM_PAT = re.compile(r'Alarm\s+([0-9A-Fa-f]{3,4})\s+has\s+been\s+terminated|/I/Alarm\s+([0-9A-Fa-f]{3,4})\s+has\s+been\s+terminated', re.IGNORECASE)
UNCONTROLLED_RESTART_PAT = re.compile(r'uncontrolled restart', re.IGNORECASE)
SOFTWARE_ERROR_PAT = re.compile(r'Software error|System error', re.IGNORECASE)
ALARM_LINE_PAT = re.compile(r'/(I|W|F)/(.+?Alarm.*)', re.IGNORECASE)  # to capture message snippet too


def extract_timestamp_from_line(line: str) -> Optional[datetime]:
    """Try several patterns to pull a datetime from a single line."""
    # ISO style "2025-07-31 22:37:42"
    m = ISO_TS.search(line)
    if m:
        try:
            return dparser.parse(m.group(1))
        except Exception:
            pass

    # TSMC embedded /YYYYMMDD/HH:MM:SS.mmm/
    m = TSMC_EMBED_TS.search(line)
    if m:
        ds, ts = m.group(1), m.group(2)
        try:
            dt = datetime.strptime(ds + ' ' + ts.split('.')[0], '%Y%m%d %H:%M:%S')
            # preserve fractional if present
            if '.' in ts:
                frac = float('0.' + ts.split('.')[1])
                dt = dt.replace(microsecond=int(frac * 1e6))
            return dt
        except Exception:
            pass

    # VDC style :)/20250808/00:00:02.227331/
    m = VDC_TS.search(line)
    if m:
        try:
            year, mon, day, ts = m.group(1), m.group(2), m.group(3), m.group(4)
            return dparser.parse(f"{year}-{mon}-{day} {ts}")
        except Exception:
            pass

    # ISO-like without separators
    m = ISO_TS_NO_SEP.search(line)
    if m:
        try:
            return dparser.parse(m.group(1))
        except Exception:
            pass

    # fallback: try to parse any leading date
    try:
        cand = line.strip().split()[0]
        if re.match(r'\d{4}-\d{2}-\d{2}', cand):
            return dparser.parse(cand)
    except Exception:
        pass

    return None


def normalize_severity_from_line(line: str) -> str:
    if '/F/' in line or r'\tF\t' in line or ' F\t' in line:
        return 'Fatal'
    if '/W/' in line or r'\tW\t' in line:
        return 'Warning'
    if '/I/' in line or r'\tI\t' in line:
        return 'Info'
    # keywords:
    if 'error' in line.lower() or 'software error' in line.lower():
        return 'Error'
    return 'Unknown'


def find_alarm_code(line: str) -> Optional[str]:
    m = re.search(r'Alarm\s+([0-9A-Fa-f]{2,4})', line, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # cases like "/W/Alarm 104A has been raised."
    m = re.search(r'/W/Alarm\s+([0-9A-Fa-f]{2,4})', line, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def parse_text_into_events(text: str, source_file: str) -> List[Dict]:
    """
    Parse raw text lines and produce a list of event dicts:
    keys: source_file, raw_line, alarm_code, event_type (Raised/Terminated/Other), severity, timestamp, message
    """
    events = []
    lines = text.splitlines()
    for idx, ln in enumerate(lines):
        line = ln.strip()
        if not line:
            continue

        # Quick filters - we only capture interesting lines (alarms, restarts, software errors, failed posts)
        interesting = False
        if 'Alarm' in line or 'uncontrolled restart' in line.lower() or 'Software error' in line or 'System error' in line or 'Failed to post' in line or 'has been raised' in line or 'has been terminated' in line:
            interesting = True

        if not interesting:
            # but we also capture lines containing '/W/' '/I/' '/F/' with "Alarm" phrase earlier/later
            if '/W/' in line or '/I/' in line or '/F/' in line:
                if 'Alarm' in line or 'restart' in line.lower() or 'Software error' in line:
                    interesting = True

        if not interesting:
            continue

        ts = extract_timestamp_from_line(line)
        sev = normalize_severity_from_line(line)
        alarm_code = find_alarm_code(line)
        message = line

        # Determine event type
        typ = None
        if re.search(r'has been raised|has been raised\.', line, re.IGNORECASE) or re.search(r'Alarm .* raised', line, re.IGNORECASE):
            typ = 'Raised'
        elif re.search(r'has been terminated|has been terminated\.', line, re.IGNORECASE) or re.search(r'Alarm .* terminated', line, re.IGNORECASE):
            typ = 'Terminated'
        elif UNCONTROLLED_RESTART_PAT.search(line):
            typ = 'UncontrolledRestart'
            # set alarm code to a special one if not present
            if not alarm_code:
                alarm_code = '108F'  # 108F used in your logs for uncontrolled restart
        elif SOFTWARE_ERROR_PAT.search(line):
            typ = 'SoftwareError'
        else:
            typ = 'Info'  # fallback

        events.append({
            "source_file": source_file,
            "raw_line": line,
            "alarm_code": alarm_code if alarm_code else '',
            "Alarm Name": alarm_code if alarm_code else '',
            "event_type": typ,
            "Severity": sev,
            "timestamp": ts,
            "Message": message,
            "index": idx
        })

    return events


def pair_raise_terminate(events: List[Dict]) -> pd.DataFrame:
    """
    From a list of parsed events (not necessarily already paired),
    create a table where each row is an alarm occurrence with Raise & Terminate times if available.
    """
    # Sort by timestamp if available else by index
    events_sorted = sorted(events, key=lambda e: (e['timestamp'] if e['timestamp'] is not None else datetime.min, e['index']))

    # We'll maintain an "open raises" map: key=(source_file, alarm_code) -> list of raise events
    open_raises = {}
    rows = []

    for ev in events_sorted:
        key = (ev['source_file'], ev['alarm_code'] or ev['Message'][:40])
        if ev['event_type'] == 'Raised':
            open_raises.setdefault(key, []).append(ev)
        elif ev['event_type'] == 'Terminated':
            # match to most recent open raise for same key
            if key in open_raises and open_raises[key]:
                raise_ev = open_raises[key].pop(0)  # FIFO pairing
                rows.append({
                    "Device Name": ev['source_file'],
                    "Alarm Name": ev['alarm_code'] or 'Unknown',
                    "Severity": raise_ev['Severity'] or ev['Severity'],
                    "Status": "Raised->Terminated",
                    "Raise Date": raise_ev['timestamp'],
                    "Terminated Date": ev['timestamp'],
                    "Duration (s)": ( (ev['timestamp'] - raise_ev['timestamp']).total_seconds() if (ev['timestamp'] and raise_ev['timestamp']) else None),
                    "Message": f"{raise_ev['Message']}  ||  {ev['Message']}",
                    "source_file": ev['source_file'],
                })
            else:
                # Terminated without a known raise: record terminated with missing raise
                rows.append({
                    "Device Name": ev['source_file'],
                    "Alarm Name": ev['alarm_code'] or 'Unknown',
                    "Severity": ev['Severity'],
                    "Status": "Terminated (no matched raise)",
                    "Raise Date": None,
                    "Terminated Date": ev['timestamp'],
                    "Duration (s)": None,
                    "Message": ev['Message'],
                    "source_file": ev['source_file'],
                })
        else:
            # For other events (software error, uncontrolled restart) record as single rows
            if ev['event_type'] in ('UncontrolledRestart', 'SoftwareError', 'Info'):
                rows.append({
                    "Device Name": ev['source_file'],
                    "Alarm Name": ev['alarm_code'] or ev['event_type'],
                    "Severity": ev['Severity'],
                    "Status": ev['event_type'],
                    "Raise Date": ev['timestamp'],
                    "Terminated Date": ev['timestamp'] if ev['event_type'] == 'Info' else None,
                    "Duration (s)": None,
                    "Message": ev['Message'],
                    "source_file": ev['source_file'],
                })

    # Any open raises left (raised but no terminated) should be recorded
    for key, lst in open_raises.items():
        for raise_ev in lst:
            rows.append({
                "Device Name": raise_ev['source_file'],
                "Alarm Name": raise_ev['alarm_code'] or 'Unknown',
                "Severity": raise_ev['Severity'],
                "Status": "Raised (no termination)",
                "Raise Date": raise_ev['timestamp'],
                "Terminated Date": None,
                "Duration (s)": None,
                "Message": raise_ev['Message'],
                "source_file": raise_ev['source_file'],
            })

    df = pd.DataFrame(rows)
    # Normalize dates to pandas datetime
    if not df.empty:
        df['Raise Date'] = pd.to_datetime(df['Raise Date'], errors='coerce')
        df['Terminated Date'] = pd.to_datetime(df['Terminated Date'], errors='coerce')
    return df


# ------------------------
# Visuals (Plotly + PIL)
# ------------------------
def plot_counts(df: pd.DataFrame):
    if df.empty:
        return px.histogram(pd.DataFrame({"No data": []}), x="No data", title="No events to plot")
    x_col = "Alarm Name" if "Alarm Name" in df.columns and df["Alarm Name"].notna().any() else "Severity"
    fig = px.histogram(df, x=x_col, title=f"Event Counts by {x_col}", text_auto=True)
    fig.update_layout(bargap=0.1)
    return fig


def plot_timeline(df: pd.DataFrame):
    if df.empty or "Raise Date" not in df.columns:
        return px.scatter(pd.DataFrame({"No data": []}), x="No data", y="No data", title="No timeline data")
    d = df.copy()
    d = d.dropna(subset=['Raise Date'])
    if d.empty:
        return px.scatter(pd.DataFrame({"No data": []}), x="No data", y="No data", title="No timeline data")
    y_col = "Alarm Name" if "Alarm Name" in d.columns else "Device Name"
    color_col = "Severity" if "Severity" in d.columns else None
    fig = px.scatter(d, x='Raise Date', y=y_col, color=color_col, hover_data=['Message', 'Status', 'source_file'])
    fig.update_layout(title="Event Timeline")
    return fig


def draw_root_cause_diagram_textlist(events: List[str]) -> Image.Image:
    """Simple PIL rendering of a root cause list diagram."""
    w, h = 900, 400
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 6), "Root Cause / Event Flow (simplified)", fill="black")
    y = 36
    max_lines = min(len(events), 20)
    for i in range(max_lines):
        txt = f"{i+1}. {events[i][:120]}"
        draw.text((10, y), txt, fill="blue")
        y += 18
    if len(events) > max_lines:
        draw.text((10, y+6), f"... ({len(events)-max_lines} more)", fill="gray")
    return img


# ------------------------
# Streamlit App
# ------------------------
st.set_page_config(page_title="Universal Log & Event Analyzer", layout="wide", initial_sidebar_state="expanded")
st.title("TSMC / Endpoint Log Analyzer — Multi-file Dashboard")

# Sidebar - file upload and filters
st.sidebar.header("Load logs")
uploaded = st.sidebar.file_uploader("Upload log file(s) (txt, log). You may upload multiple files.", type=['txt', 'log', 'log.txt', 'log1', 'csv'], accept_multiple_files=True)

help_text = st.sidebar.markdown(
    """
    - This app recognizes TSMC-style logs, McScript/McAfee logs, VDC logs (session examples).
    - Upload multiple files and use filters below to narrow events.
    """
)

# parse uploaded files or load example if none
all_events = []
source_map = {}
if uploaded:
    for up in uploaded:
        try:
            raw = up.getvalue().decode('utf-8', errors='replace')
        except Exception:
            raw = up.getvalue().decode('latin-1', errors='replace')
        events = parse_text_into_events(raw, up.name)
        all_events.extend(events)
        source_map[up.name] = len(events)
else:
    st.sidebar.info("No files uploaded yet — please upload log files to analyze.")
    # don't exit; show empty dashboard

# Convert to event table
df_events = pair_raise_terminate(all_events)

# Add alternate columns if missing
for c in ["Device Name", "Alarm Name", "Severity", "Status", "Raise Date", "Terminated Date", "Message", "source_file"]:
    if c not in df_events.columns:
        df_events[c] = None

# Sidebar filters
st.sidebar.markdown("---")
st.sidebar.header("Filters")

# Date range filter (based on Raise Date)
if not df_events.empty and df_events['Raise Date'].notna().any():
    min_dt = df_events['Raise Date'].min().date()
    max_dt = df_events['Raise Date'].max().date()
else:
    today = datetime.utcnow().date()
    min_dt = today
    max_dt = today
date_range = st.sidebar.date_input("Date range (Raise Date)", [min_dt, max_dt])

# Time filter
start_time = st.sidebar.time_input("Start time", value=time(0, 0))
end_time = st.sidebar.time_input("End time", value=time(23, 59))

severity_options = sorted(df_events['Severity'].dropna().unique()) if not df_events.empty else []
selected_sev = st.sidebar.multiselect("Severity", options=severity_options, default=severity_options)

alarm_filter = st.sidebar.text_input("Alarm name/code filter (partial)", "")
fulltext = st.sidebar.text_input("Full-text search", "")

# Which files to include
files_present = sorted(df_events['source_file'].dropna().unique()) if not df_events.empty else []
sel_files = st.sidebar.multiselect("Choose source file(s)", options=files_present, default=files_present)

st.sidebar.markdown("---")
download_button_label = st.sidebar.button("Refresh / Re-apply Filters")

# Apply filters
df_filtered = df_events.copy()
# filter by files
if sel_files:
    df_filtered = df_filtered[df_filtered['source_file'].isin(sel_files)]
# filter by severity
if selected_sev:
    df_filtered = df_filtered[df_filtered['Severity'].isin(selected_sev)]
# alarm code partial
if alarm_filter:
    df_filtered = df_filtered[df_filtered['Alarm Name'].str.contains(alarm_filter, case=False, na=False) | df_filtered['Message'].str.contains(alarm_filter, case=False, na=False)]
# fulltext
if fulltext:
    df_filtered = df_filtered[df_filtered.apply(lambda r: fulltext.lower() in str(r['Message']).lower() or fulltext.lower() in str(r['Alarm Name']).lower(), axis=1)]

# date/time filtering by Raise Date + times
def in_datetime_range(dt: pd.Timestamp, date_range: List[datetime.date], start_t: time, end_t: time) -> bool:
    if pd.isna(dt):
        return False
    d = dt.date()
    if not (date_range[0] <= d <= date_range[1]):
        return False
    t = dt.time()
    return (start_t <= t <= end_t)

if not df_filtered.empty:
    df_filtered = df_filtered[df_filtered['Raise Date'].apply(lambda x: in_datetime_range(x, date_range, start_time, end_time) if not pd.isna(x) else False)]

# ------------------------
# Main layout: KPIs and visuals
# ------------------------
st.markdown("### Summary of parsed files")
col1, col2, col3, col4 = st.columns(4)
total_files = len(files_present)
total_events = len(df_events)
critical = df_events[df_events['Severity'].isin(['Fatal', 'Error', 'Unknown'])].shape[0] if not df_events.empty else 0
unique_alarms = df_events['Alarm Name'].nunique() if not df_events.empty else 0

col1.metric("Files processed", total_files)
col2.metric("Total parsed events", total_events)
col3.metric("Critical / Error events", critical)
col4.metric("Unique alarms", unique_alarms)

st.markdown("---")
# Graphical area: timeline + counts
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("Alarm timeline")
    fig_tl = plot_timeline(df_filtered)
    st.plotly_chart(fig_tl, use_container_width=True, height=400)

    st.subheader("Top event counts")
    fig_counts = plot_counts(df_filtered)
    st.plotly_chart(fig_counts, use_container_width=True, height=300)

with right_col:
    st.subheader("Choose file for Root Cause diagram")
    rf = st.selectbox("Select file", options=files_present) if files_present else st.selectbox("Select file", options=["(no file)"])
    if rf and rf != "(no file)":
        # gather messages from that file
        msgs = df_events[df_events['source_file'] == rf]['Message'].tolist()
        img = draw_root_cause_diagram_textlist(msgs)
        st.image(img, use_column_width=True)
    else:
        st.info("Upload a file to generate diagram.")

st.markdown("---")
# Event Table + download
st.subheader("Event Details Table")
if df_filtered.empty:
    st.info("No events match filters.")
else:
    # display
    display_cols = ["Device Name", "Alarm Name", "Severity", "Status", "Raise Date", "Terminated Date", "Duration (s)", "Message", "source_file"]
    df_show = df_filtered.copy()
    # format datetime columns as strings for display
    df_show['Raise Date'] = df_show['Raise Date'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
    df_show['Terminated Date'] = df_show['Terminated Date'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
    st.dataframe(df_show[display_cols].sort_values(by="Raise Date", ascending=True), height=360)

    # download Excel
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
        df_show.to_excel(writer, index=False, sheet_name='events')
    towrite.seek(0)
    st.download_button(label="Download events as Excel", data=towrite, file_name="events.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
st.caption("Parser heuristics: if you have other log formats paste a sample and I'll extend the parser rules.")

# End


