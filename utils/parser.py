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
        return parse_text_log(text)

def parse_text_log(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()

        # --- TSMC alarm style ---
        match_tsmc = re.search(r"(/W/|/I/|/E/)?Alarm\s+([^\s]+)\s+has been\s+(raised|terminated)", line, re.IGNORECASE)
        if match_tsmc:
            severity = "Warning" if match_tsmc.group(1) == "/W/" else "Info" if match_tsmc.group(1) == "/I/" else "Error"
            rows.append({
                "Device Name": "TSMC",
                "Alarm Name": match_tsmc.group(2),
                "Severity": severity,
                "Status": match_tsmc.group(3).capitalize(),
                "Raise Date": None,
                "Terminated Date": None,
                "Message": line
            })
            continue

        # --- McAfee/McScript style ---
        match_mcafee = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+#\d+\s+(\S+)\s+(.*)$", line)
        if match_mcafee:
            ts = pd.to_datetime(match_mcafee.group(1), errors="coerce")
            module = match_mcafee.group(2)
            msg = match_mcafee.group(3)
            severity = "Info"
            if "error" in msg.lower():
                severity = "Error"
            elif "fail" in msg.lower():
                severity = "Critical"

            rows.append({
                "Device Name": module,
                "Alarm Name": module,
                "Severity": severity,
                "Status": "Info",
                "Raise Date": ts,
                "Terminated Date": None,
                "Message": msg
            })
            continue

        # --- Fallback: generic log line ---
        if line:
            rows.append({
                "Device Name": "Unknown",
                "Alarm Name": None,
                "Severity": "Info",
                "Status": "Info",
                "Raise Date": None,
                "Terminated Date": None,
                "Message": line
            })

    return pd.DataFrame(rows)

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
    top_alarms = df["Alarm Name"].value_counts().head(3).to_dict()
    return f"Period: {period}\nTotal Events: {total}\nCritical Events: {critical_count}\nTop Alarms: {top_alarms}"


