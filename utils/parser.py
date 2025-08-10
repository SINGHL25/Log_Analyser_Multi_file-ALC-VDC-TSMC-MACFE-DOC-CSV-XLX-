import pandas as pd
import re
from datetime import datetime

def load_file(file):
    """
    Load and parse a supported log file into a DataFrame.
    Supports TSMC-style logs and McScript/McAfee logs.
    """
    name = file.name.lower()
    content = file.read().decode(errors="ignore").splitlines()

    if "mcscript" in name or "mcafee" in name:
        return parse_mcscript(content)
    elif "tsmc" in name or "tp" in name or ".tsm" in name:
        return parse_tsmc(content)
    else:
        return parse_generic(content)

def parse_mcscript(lines):
    """
    Parse McScript/McAfee agent logs.
    Expected format: YYYY-MM-DD HH:MM:SS <level> ...
    """
    events = []
    for line in lines:
        m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([IWEC])\s+.*?\s+(\S+)\s+(.*)", line)
        if m:
            ts, sev, src, msg = m.groups()
            events.append({
                "Raise Date": pd.to_datetime(ts, errors="coerce"),
                "Severity": severity_map(sev),
                "Device Name": None,
                "Alarm Name": src,
                "Status": None,
                "Message": msg.strip(),
                "Terminated Date": None
            })
    return pd.DataFrame(events)

def parse_tsmc(lines):
    """
    Parse TSMC-style logs.
    Recognizes 'Alarm XYZ has been raised/terminated' and general messages.
    """
    events = []
    for line in lines:
        # Match timestamp at end of line
        ts_match = re.search(r"/(\d{8})/(\d{2}:\d{2}:\d{2}\.\d+)", line)
        timestamp = None
        if ts_match:
            date_str, time_str = ts_match.groups()
            try:
                timestamp = pd.to_datetime(date_str + " " + time_str, format="%Y%m%d %H:%M:%S.%f")
            except:
                timestamp = None

        # Alarm raised
        if "Alarm" in line and "raised" in line.lower():
            m = re.search(r"Alarm\s+([^\s]+)", line)
            alarm = m.group(1) if m else None
            events.append({
                "Raise Date": timestamp,
                "Severity": "Warning",
                "Device Name": None,
                "Alarm Name": alarm,
                "Status": "Raised",
                "Message": line.strip(),
                "Terminated Date": None
            })

        # Alarm terminated
        elif "Alarm" in line and "terminated" in line.lower():
            m = re.search(r"Alarm\s+([^\s]+)", line)
            alarm = m.group(1) if m else None
            events.append({
                "Raise Date": None,
                "Severity": "Info",
                "Device Name": None,
                "Alarm Name": alarm,
                "Status": "Terminated",
                "Message": line.strip(),
                "Terminated Date": timestamp
            })

        # Generic message
        else:
            events.append({
                "Raise Date": timestamp,
                "Severity": "Info",
                "Device Name": None,
                "Alarm Name": None,
                "Status": None,
                "Message": line.strip(),
                "Terminated Date": None
            })
    return pd.DataFrame(events)

def parse_generic(lines):
    """
    Fallback parser for unknown formats — extracts datetime and message.
    """
    events = []
    for line in lines:
        ts = None
        m = re.match(r"(\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
        if m:
            try:
                ts = pd.to_datetime(m.group(1))
            except:
                ts = None
        events.append({
            "Raise Date": ts,
            "Severity": None,
            "Device Name": None,
            "Alarm Name": None,
            "Status": None,
            "Message": line.strip(),
            "Terminated Date": None
        })
    return pd.DataFrame(events)

def severity_map(code):
    return {"I": "Info", "W": "Warning", "E": "Error", "C": "Critical"}.get(code, "Info")

def clean_events(df):
    """
    Ensure required columns exist, fill missing with None, and sort by date.
    """
    expected_cols = ["Device Name", "Alarm Name", "Severity", "Status", "Raise Date", "Terminated Date", "Message", "source_file"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    if "Raise Date" in df.columns:
        df = df.sort_values("Raise Date", na_position="last")
    return df

def generate_summary(df):
    """
    Create textual summary for display.
    """
    if "Raise Date" not in df.columns or df.empty:
        return "No date data available."

    period = f"{df['Raise Date'].min()} to {df['Raise Date'].max()}"
    total = len(df)
    critical_count = len(df[df["Severity"].str.lower().isin(["critical", "error"], na=False)]) if "Severity" in df.columns else 0
    top_alarms = df["Alarm Name"].value_counts().head(3).to_dict() if "Alarm Name" in df.columns else {}
    return f"Period: {period}\nTotal Events: {total}\nCritical Events: {critical_count}\nTop Alarms: {top_alarms}"





