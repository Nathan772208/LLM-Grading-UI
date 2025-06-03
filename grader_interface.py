import streamlit as st
import sqlite3
import pandas as pd
import re

DB_PATH = "human_eval.db"
REFERENCE_FILE = "2802_quiz3_expert.txt"

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT rowid, * FROM human_eval;", conn)
    conn.close()
    return df

def save_update(rowid, rubric_q1, rubric_q2, notes, fb_q1, fb_q2, fb_combined):
    conn = sqlite3.connect(DB_PATH)
    query = """
        UPDATE human_eval
        SET rubric_score_q1 = ?, rubric_score_q2 = ?, human_notes = ?,
            feedback_q1 = ?, feedback_q2 = ?, combined_feedback = ?
        WHERE rowid = ?
    """
    conn.execute(query, (rubric_q1, rubric_q2, notes, fb_q1, fb_q2, fb_combined, rowid))
    conn.commit()
    conn.close()

def load_reference_sections(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract quoted question and answer strings only
        questions = re.findall(r'pdf\.multi_cell\(0, 10, "(- Question 1:.*?)"\)', content, re.DOTALL)
        questions += re.findall(r'pdf\.multi_cell\(0, 10, "(- Question 2:.*?)"\)', content, re.DOTALL)

        answers = re.findall(r'pdf\.multi_cell\(0, 10, "(- Reference Answer to Question 1:.*?)"\)', content, re.DOTALL)
        answers += re.findall(r'pdf\.multi_cell\(0, 10, "(- Reference Answer to Question 2:.*?)"\)', content, re.DOTALL)

        questions_text = "\n\n".join(q.replace("- ", "") for q in questions)
        answers_text = "\n\n".join(a.replace("- ", "") for a in answers)

        return questions_text.strip(), answers_text.strip()

    except Exception as e:
        return "Error loading questions", f"Error loading answers: {e}"

# Load and prepare data
df = load_data()
options = df.to_dict("records")
questions_text, answers_text = load_reference_sections(REFERENCE_FILE)

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

with st.expander("📋 Quiz Questions"):
    st.text_area("Questions", questions_text, height=300, disabled=True)

with st.expander("✅ Expert Reference Answers"):
    st.text_area("Expert Answers", answers_text, height=300, disabled=True)

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
        save_update(selected['rowid'], score_q1, score_q2, notes, fb_q1, fb_q2, fb_combined)
        st.success("Changes saved!")

