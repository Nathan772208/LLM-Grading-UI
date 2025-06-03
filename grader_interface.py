import streamlit as st
import sqlite3
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# Load credentials from st.secrets
credentials = {
    "type": st.secrets["gspread"]["type"],
    "project_id": st.secrets["gspread"]["project_id"],
    "private_key_id": st.secrets["gspread"]["private_key_id"],
    "private_key": st.secrets["gspread"]["private_key"],
    "client_email": st.secrets["gspread"]["client_email"],
    "client_id": st.secrets["gspread"]["client_id"],
    "token_uri": st.secrets["gspread"]["token_uri"]
}

# Authenticate with Google
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(credentials, scopes=scopes)
gc = gspread.authorize(credentials)

# Open the Google Sheet
sh = gc.open("Human Feedback Database Spread Sheet")  # Replace with your actual sheet name
worksheet = sh.sheet1  # Replace with your actual worksheet

# Load data from the worksheet
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Save updates to the worksheet
def save_update(row_index, rubric_q1, rubric_q2, notes, fb_q1, fb_q2, fb_combined):
    worksheet.update_cell(row_index + 2, df.columns.get_loc("rubric_score_q1") + 1, rubric_q1)
    worksheet.update_cell(row_index + 2, df.columns.get_loc("rubric_score_q2") + 1, rubric_q2)
    worksheet.update_cell(row_index + 2, df.columns.get_loc("human_notes") + 1, notes)
    worksheet.update_cell(row_index + 2, df.columns.get_loc("feedback_q1") + 1, fb_q1)
    worksheet.update_cell(row_index + 2, df.columns.get_loc("feedback_q2") + 1, fb_q2)
    worksheet.update_cell(row_index + 2, df.columns.get_loc("combined_feedback") + 1, fb_combined)

# Load and prepare data
df = load_data()
options = df.to_dict("records")

# Helper to detect truly "filled" strings
def is_filled(series):
    return series.astype(str).str.strip().replace("None", "").replace("nan", "") != ""

# Compute grading progress
num_total = len(df)
num_complete = df[
    is_filled(df['rubric_score_q1']) &
    is_filled(df['rubric_score_q2']) &
    is_filled(df['human_notes'])
].shape[0]

# Sidebar progress
with st.sidebar:
    st.markdown("### 🧮 Grading Progress")
    st.progress(num_complete / num_total if num_total else 0)
    st.write(f"{num_complete} of {num_total} responses completed")

# Add completion filter
incomplete_only = st.checkbox("Show only unevaluated responses (missing human evaluation section)")

if incomplete_only:
    options = [
        rec for rec in options 
        if not (rec['rubric_score_q1'] and rec['rubric_score_q2'] and rec['human_notes'])
    ]

# Interface title and dropdown
st.title("LLM Feedback Grader Interface")

# Student selection
selected = st.selectbox("Select a student response:", options,
                        format_func=lambda x: f"Student ID {x['student_id']}")

if selected:
    st.subheader("Student Responses")
    st.text_area("Response to Question 1", selected['student_response_q1'], disabled=True, height=150)
    st.text_area("Response to Question 2", selected['student_response_q2'], disabled=True, height=150)

    st.subheader("Original LLM Feedback (For Reference)")
    st.text_area("Original Feedback for Q1", selected['feedback_q1'], disabled=True, height=150)
    st.text_area("Original Feedback for Q2", selected['feedback_q2'], disabled=True, height=150)
    st.text_area("Original Combined Feedback", selected['combined_feedback'], disabled=True, height=100)

    st.subheader("LLM Feedback (Editable)")
    fb_q1 = st.text_area("Feedback for Q1", value=selected['feedback_q1'] or "", height=150)
    fb_q2 = st.text_area("Feedback for Q2", value=selected['feedback_q2'] or "", height=150)
    fb_combined = st.text_area("Overall Feedback Summary", value=selected['combined_feedback'] or "", height=100)

    st.subheader("Your Evaluation")
    score_q1 = st.text_area("Grader Evaluation for Q1", value=selected['rubric_score_q1'] or "", height=80)
    score_q2 = st.text_area("Grader Evaluation for Q2", value=selected['rubric_score_q2'] or "", height=80)
    notes = st.text_area("How accurate was the LLM in providing feedback for the questions", value=selected['human_notes'] or "", height=100)

    if st.button("Save Changes"):
        row_index = df.index[df['student_id'] == selected['student_id']].tolist()[0]
        save_update(row_index, score_q1, score_q2, notes, fb_q1, fb_q2, fb_combined)
        st.success("Changes saved!")
