# streamlit_app.py
# import PyPDF2
# import re
# import pandas as pd
# import os
# import datetime as dt
# import streamlit as st
# import io
# import matplotlib.pyplot as plt
# import seaborn as sns
#from datetime import datetime

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



def show_dashboard():
    
    # Load data from session_state
    if "extracted_data" not in st.session_state:
        st.warning("⚠️ No data found. Please extract PDF data first.")
        return

    df = st.session_state["extracted_data"]

    # --- Preprocessing ---
    df['DOB'] = pd.to_datetime(df['DOB'], errors='coerce')
    df['DOS'] = pd.to_datetime(df['DOS'], errors='coerce')
    df['Anesthesia Start'] = pd.to_datetime(df['Anesthesia Start'], format='%H%M', errors='coerce').dt.time
    df['Anesthesia Stop'] = pd.to_datetime(df['Anesthesia Stop'], format='%H%M', errors='coerce').dt.time
    df['Age'] = 2025 - df['DOB'].dt.year

    bins = [0, 20, 40, 60, 100]
    labels = ['<20', '20-40', '40-60', '60+']
    df['Age Group'] = pd.cut(df['Age'], bins=bins, labels=labels, include_lowest=True)

    def calculate_duration(row):
        if pd.isna(row['Anesthesia Start']) or pd.isna(row['Anesthesia Stop']):
            return None
        start = pd.to_datetime(str(row['Anesthesia Start']), format='%H:%M:%S')
        stop = pd.to_datetime(str(row['Anesthesia Stop']), format='%H:%M:%S')
        if stop < start:
            stop += pd.Timedelta(days=1)
        return (stop - start).total_seconds() / 60

    df['Anesthesia Duration'] = df.apply(calculate_duration, axis=1)

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    gender_filter = st.sidebar.multiselect("Select Gender", options=df['Gender'].unique(), default=df['Gender'].unique())
    age_group_filter = st.sidebar.multiselect("Select Age Group", options=df['Age Group'].cat.categories, default=df['Age Group'].cat.categories)
    filtered_df = df[df['Gender'].isin(gender_filter) & df['Age Group'].isin(age_group_filter)]

    # --- Matplotlib Display Helper ---
    def display_plot(fig, title):
        st.subheader(title)
        st.pyplot(fig)

    # --- Analyses ---
    # 1. Procedure Frequency
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    filtered_df['Procedure'].value_counts().head(10).plot(kind='bar', ax=ax1)
    ax1.set_title("Top 10 Most Common Procedures")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    display_plot(fig1, "Procedure Frequency")

    # 2. Diagnosis Distribution
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    filtered_df['Diagnosis'].value_counts().head(10).plot(kind='bar', ax=ax2)
    ax2.set_title("Top 10 Most Common Diagnoses")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    display_plot(fig2, "Diagnosis Distribution")

    # 3. Gender-Based Analysis
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    gender_proc = filtered_df.groupby(['Gender', 'Procedure']).size().unstack().fillna(0)
    top_procs = gender_proc.sum().nlargest(5).index
    gender_proc[top_procs].plot(kind='bar', stacked=True, ax=ax3)
    ax3.set_title("Top 5 Procedures by Gender")
    ax3.legend(title="Procedure", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    display_plot(fig3, "Gender-Based Procedure Analysis")

    # 4. Age Group Analysis
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    age_proc = filtered_df.groupby(['Age Group', 'Procedure']).size().unstack().fillna(0)
    top_procs_age = age_proc.sum().nlargest(5).index
    age_proc[top_procs_age].plot(kind='bar', stacked=True, ax=ax4)
    ax4.set_title("Top 5 Procedures by Age Group")
    ax4.legend(title="Procedure", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    display_plot(fig4, "Age Group-Based Procedure Analysis")

    # 5. Anesthesia Duration
    fig5, ax5 = plt.subplots(figsize=(10, 6))
    dur_df = filtered_df.dropna(subset=['Anesthesia Duration'])
    top_proc_dur = dur_df['Procedure'].value_counts().head(5).index
    sns.boxplot(x='Procedure', y='Anesthesia Duration', data=dur_df[dur_df['Procedure'].isin(top_proc_dur)], ax=ax5)
    ax5.set_title("Anesthesia Duration Distribution by Procedure")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    display_plot(fig5, "Anesthesia Duration")

    # 6. Procedure Trends Over Time
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    filtered_df['DOS'].value_counts().sort_index().plot(kind='line', ax=ax6, marker='o')
    ax6.set_title("Procedures Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()
    display_plot(fig6, "Procedure Trends")

    # Interesting Fact
    st.header("Interesting Fact")
    proc_counts = filtered_df['Procedure'].value_counts()
    if not proc_counts.empty:
        top_proc = proc_counts.index[0]
        common_dx = filtered_df[filtered_df['Procedure'] == top_proc]['Diagnosis'].mode()[0]
        st.markdown(f"The most common procedure is **{top_proc}**, frequently associated with **{common_dx}**.")





st.title("PDF Data Extractor to Excel")
uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    accept_multiple_files=True
)

pdf_files = [
    file for file in uploaded_files
    if file.name.lower().endswith(".pdf")
] if uploaded_files else []

if pdf_files:
    st.success(f"{len(pdf_files)} PDF file(s) uploaded.")
    excel_buffer = io.BytesIO()
    writer = pd.ExcelWriter(excel_buffer, engine='xlsxwriter')

    excel_buffer = io.BytesIO()
all_data = []  # List to collect dataframes

for pdf_file in pdf_files:
    st.write(f"🔍 Processing file: {pdf_file.name}")
    try:
        df = extract_proc_dx(pdf_file)
        df.insert(0, "Source File", pdf_file.name)  # Optional: keep track of which file it came from
        all_data.append(df)
    except Exception as e:
        st.error(f" Error in {pdf_file.name}: {e}")

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Extracted Data")
    excel_buffer.seek(0)

    writer.close()
    excel_buffer.seek(0)

    st.download_button(
        label=" Download Extracted Excel File",
        data=excel_buffer,
        file_name="pdf_extracted_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Ask user if they want to see dashboard
    st.markdown("### 📊 Do you want to see a dashboard analysis?")
    view_dashboard = st.radio("Select an option:", ["No", "Yes"])
    st.session_state["extracted_data"] = combined_df
    # if view_dashboard == "Yes":
    #     st.markdown("## 📈 Dashboard Analysis")
    #      # ✅ import the function

# ... your existing code ...

    if view_dashboard == "Yes" and st.button("Yes, take me to Dashboard"):
        

        st.title("Surgical Procedure Analysis Dashboard")
        st.markdown("This dashboard provides insights into surgical procedures, diagnoses, gender distribution, age groups, anesthesia durations, and procedure trends over time using Matplotlib visualizations.")

        show_dashboard()

    else:
        st.info("No valid data extracted from PDFs.")
else:
    st.info(" Please upload one or more PDF files.")
