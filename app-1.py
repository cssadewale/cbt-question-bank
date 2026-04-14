"""
app.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1 — Core MVP Features:
  1. Add a new question via a form
  2. View all questions in a filterable table
  3. Delete a question
  4. Filter by subject and class level
  5. Export filtered questions as CBT Pro-ready CSV

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io

# Import all our database functions from database.py
from database import (
    initialise_database,
    add_question,
    get_questions,
    delete_question,
    get_subjects,
    get_question_count,
    get_count_by_subject,
)

# ─────────────────────────────────────────────
# APP CONFIGURATION
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="CBT Question Bank",
    page_icon="📚",
    layout="wide",           # Uses full screen width — better on tablet
    initial_sidebar_state="expanded",
)

# Initialise the database every time the app loads.
# This is safe — it only creates the table if it does not already exist.
initialise_database()

# ─────────────────────────────────────────────
# CONSTANTS — Edit these to add more options later
# ─────────────────────────────────────────────

SUBJECTS = [
    "Mathematics",
    "Further Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English Language",
    "Yoruba",
    "Economics",
    "Geography",
    "Other",
]

CLASS_LEVELS = ["JSS1", "JSS2", "JSS3", "SSS1", "SSS2", "SSS3"]

ANSWER_OPTIONS = ["A", "B", "C", "D"]

SOURCES = [
    "Self-written",
    "AI-generated",
    "WAEC 2024", "WAEC 2023", "WAEC 2022", "WAEC 2021", "WAEC 2020", "WAEC 2019",
    "NECO 2024", "NECO 2023", "NECO 2022",
    "JAMB 2024", "JAMB 2023", "JAMB 2022",
    "Textbook",
    "Other",
]


# ─────────────────────────────────────────────
# SIDEBAR — Navigation between pages
# ─────────────────────────────────────────────

st.sidebar.title("📚 CBT Question Bank")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Dashboard", "➕ Add Question", "🔍 View & Filter", "📤 Export CSV"],
)

# Show a live question count in the sidebar so you always know your bank size
total = get_question_count()
st.sidebar.markdown("---")
st.sidebar.metric("Total Questions", total)


# ─────────────────────────────────────────────
# PAGE 1 — DASHBOARD
# ─────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.title("📚 CBT Question Bank Manager")
    st.markdown("**Your permanent, organised home for every exam question.**")
    st.markdown("---")

    # Top-level summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📝 Total Questions in Bank", total)
    with col2:
        subjects_in_db = get_subjects()
        st.metric("📖 Subjects Covered", len(subjects_in_db))

    st.markdown("---")
    st.subheader("Questions by Subject")

    counts_df = get_count_by_subject()
    if counts_df.empty:
        st.info("Your question bank is empty. Go to **➕ Add Question** to get started!")
    else:
        # Display as a simple bar chart and also as a table
        st.bar_chart(counts_df.set_index("subject")["question_count"])
        st.dataframe(
            counts_df.rename(columns={"subject": "Subject", "question_count": "Questions"}),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.markdown("""
    **Quick Guide:**
    - **➕ Add Question** — Enter a new question with all options and metadata
    - **🔍 View & Filter** — Browse your bank, filter by subject/class, delete questions
    - **📤 Export CSV** — Download questions in CBT Pro format, ready to upload
    """)


# ─────────────────────────────────────────────
# PAGE 2 — ADD QUESTION
# ─────────────────────────────────────────────

elif page == "➕ Add Question":
    st.title("➕ Add a New Question")
    st.markdown("Fill in all required fields (*) and click **Save Question**.")
    st.markdown("---")

    # We use st.form so the page does not re-run on every keystroke.
    # The form only submits when the user clicks the button.
    with st.form("add_question_form", clear_on_submit=True):

        # ── Row 1: Classification ──────────────────
        st.subheader("Question Classification")
        col1, col2 = st.columns(2)

        with col1:
            subject = st.selectbox("Subject *", SUBJECTS)
            topic = st.text_input("Topic *", placeholder="e.g. Algebra, Organic Chemistry, Waves")

        with col2:
            class_level = st.selectbox("Class Level *", CLASS_LEVELS)
            subtopic = st.text_input("Subtopic (optional)", placeholder="e.g. Quadratic Equations")

        st.markdown("---")

        # ── Row 2: The Question ───────────────────
        st.subheader("Question & Options")
        question_text = st.text_area(
            "Question Text *",
            placeholder="Type the full question here...",
            height=100,
        )

        col1, col2 = st.columns(2)
        with col1:
            option_a = st.text_input("Option A *", placeholder="First answer choice")
            option_b = st.text_input("Option B *", placeholder="Second answer choice")
        with col2:
            option_c = st.text_input("Option C *", placeholder="Third answer choice")
            option_d = st.text_input("Option D *", placeholder="Fourth answer choice")

        correct_answer = st.selectbox(
            "Correct Answer *",
            ANSWER_OPTIONS,
            help="Which option is correct? A, B, C, or D"
        )

        st.markdown("---")

        # ── Row 3: Optional Metadata ──────────────
        st.subheader("Additional Information")
        col1, col2 = st.columns(2)
        with col1:
            source = st.selectbox("Source", SOURCES)
        with col2:
            st.write("")  # spacer

        explanation = st.text_area(
            "Explanation (optional)",
            placeholder="Explain why the correct answer is right. This is shown to students after they answer.",
            height=80,
        )

        st.markdown("---")

        # ── Submit Button ─────────────────────────
        submitted = st.form_submit_button("💾 Save Question", use_container_width=True)

        if submitted:
            # Validate required fields before saving
            errors = []
            if not topic.strip():
                errors.append("Topic is required.")
            if not question_text.strip():
                errors.append("Question text is required.")
            if not option_a.strip():
                errors.append("Option A is required.")
            if not option_b.strip():
                errors.append("Option B is required.")
            if not option_c.strip():
                errors.append("Option C is required.")
            if not option_d.strip():
                errors.append("Option D is required.")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # All good — save to database
                new_id = add_question(
                    subject=subject,
                    class_level=class_level,
                    topic=topic.strip(),
                    subtopic=subtopic.strip() or None,
                    question_text=question_text.strip(),
                    option_a=option_a.strip(),
                    option_b=option_b.strip(),
                    option_c=option_c.strip(),
                    option_d=option_d.strip(),
                    correct_answer=correct_answer,
                    explanation=explanation.strip() or None,
                    source=source,
                )
                st.success(f"✅ Question saved successfully! (ID: {new_id})")
                st.balloons()


# ─────────────────────────────────────────────
# PAGE 3 — VIEW & FILTER
# ─────────────────────────────────────────────

elif page == "🔍 View & Filter":
    st.title("🔍 View & Filter Questions")
    st.markdown("---")

    # ── Filter Controls ───────────────────────
    col1, col2 = st.columns(2)
    with col1:
        subject_filter = st.selectbox(
            "Filter by Subject",
            ["All"] + get_subjects(),  # "All" means no filter
        )
    with col2:
        class_filter = st.selectbox(
            "Filter by Class Level",
            ["All"] + CLASS_LEVELS,
        )

    # Fetch questions from database using the selected filters
    df = get_questions(subject_filter=subject_filter, class_filter=class_filter)

    st.markdown(f"**Showing {len(df)} question(s)**")
    st.markdown("---")

    if df.empty:
        st.info("No questions found for the selected filters.")
    else:
        # ── Display Table ─────────────────────────
        # We show a simplified view — not every column — to keep it readable
        display_cols = ["id", "subject", "class_level", "topic", "question_text", "correct_answer", "source"]
        st.dataframe(
            df[display_cols].rename(columns={
                "id": "ID",
                "subject": "Subject",
                "class_level": "Class",
                "topic": "Topic",
                "question_text": "Question",
                "correct_answer": "Answer",
                "source": "Source",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # ── Expand a Single Question ──────────────
        st.markdown("---")
        st.subheader("View Full Question Details")
        question_ids = df["id"].tolist()
        selected_id = st.selectbox("Select a Question ID to view in full:", question_ids)

        if selected_id:
            row = df[df["id"] == selected_id].iloc[0]
            with st.expander(f"Question #{selected_id} — Full Details", expanded=True):
                st.markdown(f"**Subject:** {row['subject']} | **Class:** {row['class_level']} | **Topic:** {row['topic']}")
                if row.get('subtopic'):
                    st.markdown(f"**Subtopic:** {row['subtopic']}")
                st.markdown(f"**Question:** {row['question_text']}")
                st.markdown(f"- A: {row['option_a']}")
                st.markdown(f"- B: {row['option_b']}")
                st.markdown(f"- C: {row['option_c']}")
                st.markdown(f"- D: {row['option_d']}")
                st.markdown(f"**✅ Correct Answer:** {row['correct_answer']}")
                if row.get('explanation'):
                    st.markdown(f"**Explanation:** {row['explanation']}")
                st.markdown(f"**Source:** {row['source']} | **Date Added:** {row['date_added']}")

        # ── Delete a Question ─────────────────────
        st.markdown("---")
        st.subheader("🗑️ Delete a Question")
        st.warning("⚠️ Deletion is permanent. Double-check the ID before proceeding.")

        delete_id = st.number_input("Enter the Question ID to delete:", min_value=1, step=1)
        if st.button("🗑️ Delete This Question", type="primary"):
            success = delete_question(int(delete_id))
            if success:
                st.success(f"✅ Question #{delete_id} deleted.")
                st.rerun()  # Refresh the page to reflect the deletion
            else:
                st.error(f"❌ No question found with ID {delete_id}.")


# ─────────────────────────────────────────────
# PAGE 4 — EXPORT CSV
# ─────────────────────────────────────────────

elif page == "📤 Export CSV":
    st.title("📤 Export to CBT Pro CSV")
    st.markdown("Choose your filters, then download the CSV — ready to upload directly to CBT Pro.")
    st.markdown("---")

    # ── Filter Controls ───────────────────────
    col1, col2 = st.columns(2)
    with col1:
        subject_filter = st.selectbox("Subject", ["All"] + get_subjects())
    with col2:
        class_filter = st.selectbox("Class Level", ["All"] + CLASS_LEVELS)

    # Fetch matching questions
    df = get_questions(subject_filter=subject_filter, class_filter=class_filter)
    st.markdown(f"**{len(df)} question(s) match your filters.**")

    if df.empty:
        st.info("No questions to export. Adjust your filters or add questions first.")
    else:
        # ── Preview ────────────────────────────────
        st.subheader("Preview (first 5 questions)")
        preview_cols = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
        st.dataframe(df[preview_cols].head(5), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Build CBT Pro CSV ─────────────────────
        # This is the exact format required by CBT Pro:
        # Columns: Question, A, B, C, D, Answer, Explanation
        export_df = pd.DataFrame({
            "Question":    df["question_text"],
            "A":           df["option_a"],
            "B":           df["option_b"],
            "C":           df["option_c"],
            "D":           df["option_d"],
            "Answer":      df["correct_answer"],
            "Explanation": df["explanation"].fillna(""),  # Replace NULL with empty string
        })

        # Check if any Yoruba subject is included — if so, use UTF-8-BOM encoding
        # UTF-8-BOM helps Excel and some CBT platforms correctly read special characters
        has_yoruba = "Yoruba" in df["subject"].values if not df.empty else False
        encoding = "utf-8-sig" if has_yoruba else "utf-8"  # utf-8-sig = UTF-8 with BOM

        # Convert DataFrame to CSV in memory (no file saved to disk here)
        # io.BytesIO lets us create a downloadable file in memory
        csv_buffer = io.BytesIO()
        export_df.to_csv(csv_buffer, index=False, encoding=encoding)
        csv_bytes = csv_buffer.getvalue()

        # ── Build filename ────────────────────────
        subject_label = subject_filter.replace(" ", "_") if subject_filter != "All" else "All_Subjects"
        class_label   = class_filter if class_filter != "All" else "All_Classes"
        filename = f"CBTPro_{subject_label}_{class_label}_{len(df)}questions.csv"

        # ── Download Button ───────────────────────
        st.download_button(
            label=f"⬇️ Download {len(df)} Questions as CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.info(f"""
        **File details:**
        - Filename: `{filename}`
        - Encoding: `{encoding}` {'(UTF-8 with BOM for Yoruba)' if has_yoruba else '(standard UTF-8)'}
        - Format: CBT Pro compatible (Question, A, B, C, D, Answer, Explanation)
        - Questions included: {len(df)}
        """)
