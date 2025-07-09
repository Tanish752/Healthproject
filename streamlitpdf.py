import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
