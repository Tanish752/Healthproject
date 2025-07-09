import PyPDF2,re,pandas as pd, os, datetime as dt, streamlit as st
def clean(val):
    return str(val).strip().replace('\n', ' ').replace('\r', '').replace('  ', ' ')

def extract_proc_dx(pdf_stream):
    pdf_file = PyPDF2.PdfReader(pdf_stream)
    text = ""
    for i in range(len(pdf_file.pages)):
        text += pdf_file.pages[i].extract_text()
    
    # ...[all your regex extraction logic remains unchanged]...
    name_match = re.search(r'PATIENT:+(.*?)(?=\sContact)', text, re.IGNORECASE)
    sex_match = re.search(r'Sex:\s*(.*?)(?=\sCell)', text, re.IGNORECASE)
    dob_match = re.search(r'DOB\s*[:=]?\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
    #op_note_match = re.search(r'OP Note\s*\n\s*No notes found\.?', text, re.IGNORECASE)
    op_note_match = re.search(r'OP\sNote\sby\s*(.*?)', text, re.IGNORECASE)
    post_anes_summary = re.search(r'POSTANESTHESIA\sEVALUATION.*?(?=\sOP Note\s|\$)', text, re.IGNORECASE | re.DOTALL)
    case_summary_match = re.search(r'Case Summary\s+(.*?)\s+Plan Summary', text, re.DOTALL | re.IGNORECASE) 
    case_summary = case_summary_match.group(0)
    if post_anes_summary:
        summary_text = clean(post_anes_summary.group(0))
        # print(summary_text)
        proc_match = re.search(r'Procedure\(s\)\s*(.*?)(?=\s*Cooperates|\n|Last\s+edited|\)|\$)', summary_text, re.IGNORECASE)
        #proc_match = re.search(r'Procedure\(s\)\s*(.*?\((?:Right|Left):\s*[^)]+\))', summary_text, re.IGNORECASE)
    else:
        proc_match = re.search(r'Procedure\s*\[\s*Codes?\s*\]\s*(.*?)\s*(?=Diagnosis\s*\[\s*Codes?\s*\]|\[|\$|Plan\s*Summary)',case_summary,re.IGNORECASE)
    dx_match = re.search(r'Diagnosis\s*\[Codes\]\s*(.*?)\s*(?=Procedure\s*Codes|Plan\s*Summary|$)', case_summary, re.IGNORECASE | re.DOTALL)


    block_match = re.search(r"Perineural\s+Procedure\s+Note\s*(.*?)(?=\s*Electronically\s+Signed|$)",text,re.DOTALL | re.IGNORECASE)
    if block_match:
        block_text = block_match.group(0)
        # print(block_text)
        block_name_match = re.search(r'\bNerve\s*block\s*[:\-]?\s*(.*?)(?=\n|Last\s+edited|\)|\$)',block_text,re.IGNORECASE)
        if block_name_match:
            block_name = block_name_match.group(1)
        else:
            block_name = "Not found"
    else:
        block_name = "Not found"
   
    date_match = re.search(r'Date\s*[:=]?\s*(\d{1,2}/\d{1,2}/\d{4})', text)

    name = name_match.group(1).strip().replace('\n', ' ') if name_match else "Not found"
    gender = sex_match.group(1).strip().replace('\n', ' ') if sex_match else "Not found"
    dob = dob_match.group(1).strip().replace('\n', ' ') if dob_match else "Not found"
    procedure = proc_match.group(0).strip().replace('\n', ' ') if proc_match else "Not found"
    diagnosis = dx_match.group(1).strip().replace('\n', ' ') if dx_match else "Not found"
    DOS = date_match.group(1) if date_match else "Not found"

    events = {
         "anesthesia_start": r"(\s\d{4})\s+Anesthesia\s*Start",
        
        "anesthesia_stop": r"(\d{4})\s+Anesthesia\s*Stop",
        
    }

    # # Now, we use the regex patterns to populate the events dictionary
    for event, pattern in events.items():
        match = re.search(pattern, text, re.IGNORECASE)
        events[event] = match.group(1) if match else "Not found"

    row = {
        "Patient_name": name,
        "DOB": dob,
        "Gender": gender,
        "DOS": DOS,
        "Procedure": procedure,
        "Diagnosis": diagnosis,
        "Anesthesia Start": events["anesthesia_start"],
        "Anesthesia Stop": events["anesthesia_stop"]
    }

    df = pd.DataFrame([row])

    # Clean up DOB, calculate Age, Duration
    df['DOB'] = pd.to_datetime(df['DOB'], format='mixed', dayfirst=True, errors='coerce')
    df['Age'] = dt.datetime.now().year - df['DOB'].dt.year

    def format_time_string(t):
        if pd.isna(t) or t == "Not found":
            return None
        t = str(t).strip()
        if len(t) == 4 and t.isdigit():
            hour, minute = int(t[:2]), int(t[2:])
            if 0 <= hour < 24 and 0 <= minute < 60:
                return f"{hour:02d}:{minute:02d}:00"
        return None

    def calculate_duration(row):
        start_str = format_time_string(row['Anesthesia Start'])
        stop_str = format_time_string(row['Anesthesia Stop'])
        if not start_str or not stop_str:
            return None
        start = pd.to_datetime(start_str, format='%H:%M:%S')
        stop = pd.to_datetime(stop_str, format='%H:%M:%S')
        if stop < start:
            stop += pd.Timedelta(days=1)
        return (stop - start).total_seconds() / 60

    df['Anesthesia Duration'] = df.apply(calculate_duration, axis=1)
    df["Procedure"] = df["Procedure"].str.replace('Procedure(s)', '', regex=False)

    return df
