import pandas as pd
import json
import docx
import pdfplumber

def load_file(file):
    ext = file.name.split(".")[-1].lower()
    if ext in ["csv"]:
        return pd.read_csv(file)
    elif ext in ["xls", "xlsx"]:
        return pd.read_excel(file)
    elif ext == "json":
        return pd.json_normalize(json.load(file))
    elif ext == "txt":
        return parse_txt(file)
    elif ext == "pdf":
        return parse_pdf(file)
    elif ext == "docx":
        return parse_docx(file)
    else:
        return None

def parse_txt(file):
    lines = file.read().decode(errors="ignore").splitlines()
    return pd.DataFrame({"raw_line": lines})

def parse_pdf(file):
    text_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text_data.extend(page.extract_text().splitlines())
    return pd.DataFrame({"raw_line": text_data})

def parse_docx(file):
    doc = docx.Document(file)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return pd.DataFrame({"raw_line": lines})

def clean_events(df):
    df2 = df.copy()
    for col in ["Raise Date", "Terminated Date"]:
        if col in df2.columns:
            df2[col] = pd.to_datetime(df2[col], errors="coerce")
    if "Severity" in df2.columns:
        df2["Severity"] = df2["Severity"].fillna("Unknown")
    return df2, 0

def generate_summary(df):
    total = len(df)
    critical_count = df[df.get("Severity", "").str.lower() == "critical"].shape[0] if "Severity" in df.columns else 0
    top_alarms = df["Alarm Name"].value_counts().head(3).to_dict() if "Alarm Name" in df.columns else {}
    return f"""
Period: {df['Raise Date'].min()} to {df['Raise Date'].max()}
Total Events: {total}
Critical Events: {critical_count}
Top Alarms: {top_alarms}
"""
