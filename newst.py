# streamlit_app.py
from streamlitpdf import show_dashboard
import io
import streamlit as st
import pandas as pd
from finalpdfreader import extract_proc_dx
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns

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
