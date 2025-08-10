EXPECTED_COLS = [
    "Device Name", "Alarm Name", "Severity", "Status",
    "Raise Date", "Terminated Date", "Message", "source_file"
]

def parse_text_log(text, source_name=""):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        dt = extract_datetime(line)

        # TSMC Alarm format
        m_tsmc = re.search(r"(/W/|/I/|/E/)?Alarm\s+([^\s]+)\s+has been\s+(raised|terminated)", line, re.IGNORECASE)
        if m_tsmc:
            severity_map = {"/W/": "Warning", "/I/": "Info", "/E/": "Error"}
            severity = severity_map.get(m_tsmc.group(1) or "", "Info")
            rows.append({
                "Device Name": "TSMC",
                "Alarm Name": m_tsmc.group(2),
                "Severity": severity,
                "Status": m_tsmc.group(3).capitalize(),
                "Raise Date": dt,
                "Terminated Date": None,
                "Message": line,
                "source_file": source_name
            })
            continue

        # McAfee style logs
        m_mcafee = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if m_mcafee:
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
                "Raise Date": pd.to_datetime(m_mcafee.group(1), errors="coerce"),
                "Terminated Date": None,
                "Message": line,
                "source_file": source_name
            })
            continue

        # Generic fallback
        rows.append({
            "Device Name": "Unknown",
            "Alarm Name": None,
            "Severity": "Info",
            "Status": "Info",
            "Raise Date": dt,
            "Terminated Date": None,
            "Message": line,
            "source_file": source_name
        })

    df = pd.DataFrame(rows)

    # Ensure all expected columns exist
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = None

    return df[EXPECTED_COLS]  # return in fixed order




