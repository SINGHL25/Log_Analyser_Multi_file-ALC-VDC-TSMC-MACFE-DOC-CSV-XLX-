import pandas as pd
import re
from datetime import datetime

def load_file(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif filename.endswith((".xls", ".xlsx")):
        return pd.read_excel(uploaded_file)
    elif filename.endswith(".json"):
        return pd.read_json(uploaded_file)
    else:
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        return parse_text_log(text, uploaded_file.name)

def parse_text_log(text, source_name=""):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1) TSMC alarms
        m_tsmc = re.search(r"(/W/|/I/|/E/)?Alarm\s+([^\s]+)\s+has been\s+(raised|terminated)", line, re.IGNORECASE)
        if m_tsmc:
            severity = {"": "Info", "/W/": "Warning", "/I/": "Info", "/E/": "Error"}.get(m_tsmc.group(1) or "", "Info")
            rows.append({
                "Device Name": "TSMC",
                "Alarm Name": m_tsmc.group(2),
                "Severity": severity,
                "Status": m_tsmc.group(3).capitalize(),
                "Raise Date": extract_datetime(line),
                "Terminated Date": None,
                "Message": line,
                "source_file": source_name
            })
            continue

        # 2) McAfee style
        m_mcafee = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if m_mcafee:
            ts = pd.to_datetime(m_mcafee.group(1), errors="coerce")
            severity = "Info"
            if "error" in line.lower():
                severity = "Error"
            elif "fail" in line.lower():
                severity = "Critical"
            rows.append({
                "Device Name": "McAfee",
                "Alarm Name": None,
                "Severity": severity,
                "Status": "Info",
                "Raise Date": ts,
                "Terminated Date": None,
                "Message": line,
                "source_file": source_name
            })
            continue

        # 3) Generic catch-all
        rows.append({
            "Device Name": "Unknown",
            "Alarm Name": None,
            "Severity": "Info",
            "Status": "Info",
            "Raise Date": extract_datetime(line),
            "Terminated Date": None,
            "Message": line,
            "source_file": source_name
        })

    return pd.DataFrame(rows)

def extract_datetime(text):
    """Extract first timestamp-like pattern from text."""
    patterns = [
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
        r"\d{8}/\d{2}:\d{2}:\d{2}\.\d+"
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                return pd.to_datetime(m.group(0), errors="coerce")
            except:
                pass
    return pd.NaT

def clean_events(df):
    for col in ["Raise Date", "Terminated Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def generate_summary(df):
    if df.empty:
        return "No events found."
    period = f"{df['Raise Date'].min()} to {df['Raise Date'].max()}" if "Raise Date" in df.columns else "N/A"
    total = len(df)
    critical_count = (df["Severity"].str.lower() == "critical").sum()
    top_alarms = df["Alarm Name"].dropna().value_counts().head(3).to_dict()
    return f"Period: {period}\nTotal Events: {total}\nCritical Events: {critical_count}\nTop Alarms: {top_alarms}"



