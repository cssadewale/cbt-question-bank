"""
app.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1: Add question, view/filter, delete, export CSV
Phase 2: Full-text search, edit question, bulk CSV import

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io

from database import (
    initialise_database,
    add_question,
    get_questions,
    delete_question,
    get_subjects,
    get_question_count,
    get_count_by_subject,
    # Phase 2 imports
    search_questions,
    update_question,
    bulk_insert_questions,
)

# ─────────────────────────────────────────────
# APP CONFIGURATION
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="CBT Question Bank",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialise_database()

# ─────────────────────────────────────────────
# CONSTANTS
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
    "Bulk Import",
    "Other",
]

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

st.sidebar.title("📚 CBT Question Bank")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    [
        "🏠 Dashboard",
        "➕ Add Question",
        "🔍 View & Filter",
        "✏️ Edit Question",       # Phase 2
        "📥 Bulk Import",          # Phase 2
        "📤 Export CSV",
    ],
)

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
        st.bar_chart(counts_df.set_index("subject")["question_count"])
        st.dataframe(
            counts_df.rename(columns={"subject": "Subject", "question_count": "Questions"}),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.markdown("""
    **Quick Guide:**
    - **➕ Add Question** — Enter a new question manually
    - **🔍 View & Filter** — Browse, search, filter, and delete questions
    - **✏️ Edit Question** — Modify any existing question by ID
    - **📥 Bulk Import** — Upload a CSV file to import many questions at once
    - **📤 Export CSV** — Download questions in CBT Pro format
    """)


# ─────────────────────────────────────────────
# PAGE 2 — ADD QUESTION
# ─────────────────────────────────────────────

elif page == "➕ Add Question":
    st.title("➕ Add a New Question")
    st.markdown("Fill in all required fields (*) and click **Save Question**.")
    st.markdown("---")

    with st.form("add_question_form", clear_on_submit=True):

        st.subheader("Question Classification")
        col1, col2 = st.columns(2)
        with col1:
            subject = st.selectbox("Subject *", SUBJECTS)
            topic = st.text_input("Topic *", placeholder="e.g. Algebra, Organic Chemistry, Waves")
        with col2:
            class_level = st.selectbox("Class Level *", CLASS_LEVELS)
            subtopic = st.text_input("Subtopic (optional)", placeholder="e.g. Quadratic Equations")

        st.markdown("---")
        st.subheader("Question & Options")

        question_text = st.text_area("Question Text *", placeholder="Type the full question here...", height=100)

        col1, col2 = st.columns(2)
        with col1:
            option_a = st.text_input("Option A *")
            option_b = st.text_input("Option B *")
        with col2:
            option_c = st.text_input("Option C *")
            option_d = st.text_input("Option D *")

        correct_answer = st.selectbox("Correct Answer *", ANSWER_OPTIONS)

        st.markdown("---")
        st.subheader("Additional Information")

        col1, col2 = st.columns(2)
        with col1:
            source = st.selectbox("Source", SOURCES)

        explanation = st.text_area("Explanation (optional)", height=80,
                                   placeholder="Explain why the correct answer is right.")

        st.markdown("---")
        submitted = st.form_submit_button("💾 Save Question", use_container_width=True)

        if submitted:
            errors = []
            if not topic.strip():        errors.append("Topic is required.")
            if not question_text.strip(): errors.append("Question text is required.")
            if not option_a.strip():     errors.append("Option A is required.")
            if not option_b.strip():     errors.append("Option B is required.")
            if not option_c.strip():     errors.append("Option C is required.")
            if not option_d.strip():     errors.append("Option D is required.")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                new_id = add_question(
                    subject=subject, class_level=class_level,
                    topic=topic.strip(), subtopic=subtopic.strip() or None,
                    question_text=question_text.strip(),
                    option_a=option_a.strip(), option_b=option_b.strip(),
                    option_c=option_c.strip(), option_d=option_d.strip(),
                    correct_answer=correct_answer,
                    explanation=explanation.strip() or None,
                    source=source,
                )
                st.success(f"✅ Question saved successfully! (ID: {new_id})")
                st.balloons()


# ─────────────────────────────────────────────
# PAGE 3 — VIEW & FILTER (now includes search)
# ─────────────────────────────────────────────

elif page == "🔍 View & Filter":
    st.title("🔍 View & Filter Questions")
    st.markdown("---")

    # ── Search Bar (Phase 2) ──────────────────
    st.subheader("Search")
    search_query = st.text_input(
        "Search across all question text, topics, and explanations:",
        placeholder="e.g. quadratic, velocity, photosynthesis, WAEC...",
    )

    st.markdown("---")

    # ── Filter Controls ───────────────────────
    st.subheader("Filter")
    col1, col2 = st.columns(2)
    with col1:
        subject_filter = st.selectbox("Filter by Subject", ["All"] + get_subjects())
    with col2:
        class_filter = st.selectbox("Filter by Class Level", ["All"] + CLASS_LEVELS)

    # ── Decide which data to show ─────────────
    # If the user typed a search query, search takes priority.
    # Otherwise, use the subject/class filters.
    # This keeps the logic simple and predictable.

    if search_query.strip():
        df = search_questions(search_query.strip())
        # Apply subject/class filters on top of search results if set
        if subject_filter != "All":
            df = df[df["subject"] == subject_filter]
        if class_filter != "All":
            df = df[df["class_level"] == class_filter]
        st.markdown(f"**Search results for '{search_query}': {len(df)} question(s) found**")
    else:
        df = get_questions(subject_filter=subject_filter, class_filter=class_filter)
        st.markdown(f"**Showing {len(df)} question(s)**")

    st.markdown("---")

    if df.empty:
        st.info("No questions found. Try a different search term or filter.")
    else:
        # ── Display Table ─────────────────────
        display_cols = ["id", "subject", "class_level", "topic", "question_text", "correct_answer", "source"]
        st.dataframe(
            df[display_cols].rename(columns={
                "id": "ID", "subject": "Subject", "class_level": "Class",
                "topic": "Topic", "question_text": "Question",
                "correct_answer": "Answer", "source": "Source",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # ── Expand Full Question Details ──────
        st.markdown("---")
        st.subheader("View Full Question Details")
        question_ids = df["id"].tolist()
        selected_id = st.selectbox("Select a Question ID to view in full:", question_ids)

        if selected_id:
            row = df[df["id"] == selected_id].iloc[0]
            with st.expander(f"Question #{selected_id} — Full Details", expanded=True):
                st.markdown(f"**Subject:** {row['subject']} | **Class:** {row['class_level']} | **Topic:** {row['topic']}")
                if pd.notna(row.get('subtopic')) and row.get('subtopic'):
                    st.markdown(f"**Subtopic:** {row['subtopic']}")
                st.markdown(f"**Question:** {row['question_text']}")
                st.markdown(f"- A: {row['option_a']}")
                st.markdown(f"- B: {row['option_b']}")
                st.markdown(f"- C: {row['option_c']}")
                st.markdown(f"- D: {row['option_d']}")
                st.markdown(f"**✅ Correct Answer:** {row['correct_answer']}")
                if pd.notna(row.get('explanation')) and row.get('explanation'):
                    st.markdown(f"**Explanation:** {row['explanation']}")
                st.markdown(f"**Source:** {row['source']} | **Date Added:** {row['date_added']}")
                # Shortcut to edit this question
                st.info(f"To edit this question, go to **✏️ Edit Question** and enter ID **{selected_id}**.")

        # ── Delete ────────────────────────────
        st.markdown("---")
        st.subheader("🗑️ Delete a Question")
        st.warning("⚠️ Deletion is permanent. Double-check the ID before proceeding.")

        delete_id = st.number_input("Enter the Question ID to delete:", min_value=1, step=1)
        if st.button("🗑️ Delete This Question", type="primary"):
            success = delete_question(int(delete_id))
            if success:
                st.success(f"✅ Question #{delete_id} deleted.")
                st.rerun()
            else:
                st.error(f"❌ No question found with ID {delete_id}.")


# ─────────────────────────────────────────────
# PAGE 4 — EDIT QUESTION (Phase 2)
# ─────────────────────────────────────────────

elif page == "✏️ Edit Question":
    st.title("✏️ Edit an Existing Question")
    st.markdown("Enter the Question ID to load it, make your changes, then save.")
    st.markdown("---")

    # Step 1: Enter the ID to load
    edit_id = st.number_input("Question ID to edit:", min_value=1, step=1, value=1)
    load_button = st.button("📂 Load Question")

    # We use session_state to remember which question is loaded.
    # Without this, every widget interaction would reset the form.
    # session_state is Streamlit's way of storing data between reruns.
    if load_button:
        all_questions = get_questions()  # Fetch all so we can look up by ID
        match = all_questions[all_questions["id"] == edit_id]

        if match.empty:
            st.error(f"❌ No question found with ID {edit_id}. Check the ID and try again.")
        else:
            # Store the loaded question in session_state
            st.session_state["edit_question"] = match.iloc[0].to_dict()
            st.success(f"✅ Question #{edit_id} loaded. Edit the fields below and click Save.")

    # Step 2: Show the edit form if a question is loaded
    if "edit_question" in st.session_state:
        q = st.session_state["edit_question"]

        st.markdown("---")
        st.markdown(f"**Editing Question ID: {q['id']}** | Originally added: {q['date_added']}")

        with st.form("edit_question_form"):

            st.subheader("Question Classification")
            col1, col2 = st.columns(2)
            with col1:
                # index= sets the dropdown to the currently saved value
                subject = st.selectbox(
                    "Subject *", SUBJECTS,
                    index=SUBJECTS.index(q["subject"]) if q["subject"] in SUBJECTS else 0
                )
                topic = st.text_input("Topic *", value=q["topic"])
            with col2:
                class_level = st.selectbox(
                    "Class Level *", CLASS_LEVELS,
                    index=CLASS_LEVELS.index(q["class_level"]) if q["class_level"] in CLASS_LEVELS else 0
                )
                subtopic = st.text_input("Subtopic (optional)", value=q["subtopic"] or "")

            st.markdown("---")
            st.subheader("Question & Options")

            question_text = st.text_area("Question Text *", value=q["question_text"], height=100)

            col1, col2 = st.columns(2)
            with col1:
                option_a = st.text_input("Option A *", value=q["option_a"])
                option_b = st.text_input("Option B *", value=q["option_b"])
            with col2:
                option_c = st.text_input("Option C *", value=q["option_c"])
                option_d = st.text_input("Option D *", value=q["option_d"])

            correct_answer = st.selectbox(
                "Correct Answer *", ANSWER_OPTIONS,
                index=ANSWER_OPTIONS.index(q["correct_answer"]) if q["correct_answer"] in ANSWER_OPTIONS else 0
            )

            st.markdown("---")
            st.subheader("Additional Information")
            col1, col2 = st.columns(2)
            with col1:
                source = st.selectbox(
                    "Source", SOURCES,
                    index=SOURCES.index(q["source"]) if q["source"] in SOURCES else 0
                )

            explanation = st.text_area("Explanation (optional)", value=q["explanation"] or "", height=80)

            st.markdown("---")
            save_button = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if save_button:
                errors = []
                if not topic.strip():         errors.append("Topic is required.")
                if not question_text.strip(): errors.append("Question text is required.")
                if not option_a.strip():      errors.append("Option A is required.")
                if not option_b.strip():      errors.append("Option B is required.")
                if not option_c.strip():      errors.append("Option C is required.")
                if not option_d.strip():      errors.append("Option D is required.")

                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    success = update_question(
                        question_id=int(q["id"]),
                        subject=subject, class_level=class_level,
                        topic=topic.strip(), subtopic=subtopic.strip() or None,
                        question_text=question_text.strip(),
                        option_a=option_a.strip(), option_b=option_b.strip(),
                        option_c=option_c.strip(), option_d=option_d.strip(),
                        correct_answer=correct_answer,
                        explanation=explanation.strip() or None,
                        source=source,
                    )
                    if success:
                        st.success(f"✅ Question #{q['id']} updated successfully!")
                        # Clear the loaded question from memory so the form resets
                        del st.session_state["edit_question"]
                        st.rerun()
                    else:
                        st.error("❌ Update failed. The question ID may no longer exist.")


# ─────────────────────────────────────────────
# PAGE 5 — BULK IMPORT (Phase 2)
# ─────────────────────────────────────────────

elif page == "📥 Bulk Import":
    st.title("📥 Bulk Import from CSV")
    st.markdown("Upload a CSV file to import many questions at once.")
    st.markdown("---")

    # ── Format Guide ──────────────────────────
    with st.expander("📋 Accepted CSV Formats — click to expand", expanded=False):
        st.markdown("""
        **Format 1 — CBT Pro format** (your existing export files):
        ```
        Question,A,B,C,D,Answer,Explanation
        ```
        When using this format, you will be asked to fill in subject, class level,
        topic, and source once for the entire file — same values apply to all rows.

        ---

        **Format 2 — Full format** (includes all metadata per question):
        ```
        subject,class_level,topic,subtopic,question_text,option_a,option_b,option_c,option_d,correct_answer,explanation,source
        ```
        Each row carries its own subject, class, and topic.
        Use this format when importing questions from multiple subjects at once.

        ---

        **Rules for both formats:**
        - First row must be the header (column names)
        - correct_answer / Answer column must be A, B, C, or D (capital letters)
        - Explanation column is optional — leave it blank if not available
        - Save your file as CSV (comma-separated), not Excel .xlsx
        - Encoding: UTF-8 preferred; UTF-8-BOM also accepted (for Yoruba)
        """)

        # Provide a downloadable template for each format
        template_cbt = pd.DataFrame(columns=["Question", "A", "B", "C", "D", "Answer", "Explanation"])
        template_full = pd.DataFrame(columns=[
            "subject", "class_level", "topic", "subtopic",
            "question_text", "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "explanation", "source"
        ])

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download CBT Pro Template",
                template_cbt.to_csv(index=False),
                file_name="template_cbt_pro_format.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                "⬇️ Download Full Format Template",
                template_full.to_csv(index=False),
                file_name="template_full_format.csv",
                mime="text/csv",
            )

    st.markdown("---")

    # ── File Upload ───────────────────────────
    uploaded_file = st.file_uploader("Upload your CSV file:", type=["csv"])

    if uploaded_file:

        # Try to read the CSV — handle encoding issues gracefully
        try:
            # Try UTF-8 first, then fall back to latin-1 which reads almost anything
            try:
                raw_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            except UnicodeDecodeError:
                uploaded_file.seek(0)  # Reset file pointer before re-reading
                raw_df = pd.read_csv(uploaded_file, encoding="latin-1")

            st.success(f"✅ File read successfully — {len(raw_df)} rows found.")

        except Exception as e:
            st.error(f"❌ Could not read the file: {e}")
            st.stop()

        # ── Detect which format was uploaded ──
        columns_lower = [c.lower().strip() for c in raw_df.columns]

        is_cbt_format = "question" in columns_lower and "a" in columns_lower and "answer" in columns_lower
        is_full_format = "question_text" in columns_lower and "subject" in columns_lower

        if not is_cbt_format and not is_full_format:
            st.error("""
            ❌ Column headers not recognised. 
            Your file must have either CBT Pro format headers 
            (Question, A, B, C, D, Answer) or Full format headers 
            (subject, class_level, topic, question_text...).
            Download a template above to see the exact format needed.
            """)
            st.stop()

        # ── CBT Pro Format: ask for shared metadata ──
        if is_cbt_format:
            st.info("📌 CBT Pro format detected. Please fill in the metadata that will apply to ALL questions in this file.")
            col1, col2 = st.columns(2)
            with col1:
                bulk_subject = st.selectbox("Subject for all questions *", SUBJECTS, key="bulk_subject")
                bulk_topic   = st.text_input("Topic for all questions *", key="bulk_topic",
                                              placeholder="e.g. Algebra")
            with col2:
                bulk_class   = st.selectbox("Class Level for all questions *", CLASS_LEVELS, key="bulk_class")
                bulk_source  = st.selectbox("Source for all questions", SOURCES, key="bulk_source")

            bulk_subtopic = st.text_input("Subtopic (optional, applies to all)", key="bulk_subtopic")

        # ── Preview the data ──────────────────
        st.markdown("---")
        st.subheader(f"Preview — first 5 rows of {len(raw_df)} total")
        st.dataframe(raw_df.head(5), use_container_width=True, hide_index=True)

        # ── Validate and prepare questions ────
        st.markdown("---")
        st.subheader("Validation")

        questions_to_import = []
        validation_errors   = []

        for i, row in raw_df.iterrows():
            row_num = i + 2  # +2 because row 1 is the header, and humans count from 1

            if is_cbt_format:
                # Map CBT Pro columns to our database schema
                q_text  = str(row.get("Question", "")).strip()
                opt_a   = str(row.get("A", "")).strip()
                opt_b   = str(row.get("B", "")).strip()
                opt_c   = str(row.get("C", "")).strip()
                opt_d   = str(row.get("D", "")).strip()
                answer  = str(row.get("Answer", "")).strip().upper()
                expl    = str(row.get("Explanation", "")).strip()

                q_dict = {
                    "subject":       bulk_subject if is_cbt_format else "",
                    "class_level":   bulk_class   if is_cbt_format else "",
                    "topic":         bulk_topic   if is_cbt_format else "",
                    "subtopic":      bulk_subtopic if is_cbt_format else None,
                    "question_text": q_text,
                    "option_a":      opt_a,
                    "option_b":      opt_b,
                    "option_c":      opt_c,
                    "option_d":      opt_d,
                    "correct_answer": answer,
                    "explanation":   expl if expl and expl.lower() != "nan" else None,
                    "source":        bulk_source  if is_cbt_format else "Bulk Import",
                }

            else:
                # Full format — each row has its own metadata
                q_dict = {
                    "subject":        str(row.get("subject", "")).strip(),
                    "class_level":    str(row.get("class_level", "")).strip(),
                    "topic":          str(row.get("topic", "")).strip(),
                    "subtopic":       str(row.get("subtopic", "")).strip() or None,
                    "question_text":  str(row.get("question_text", "")).strip(),
                    "option_a":       str(row.get("option_a", "")).strip(),
                    "option_b":       str(row.get("option_b", "")).strip(),
                    "option_c":       str(row.get("option_c", "")).strip(),
                    "option_d":       str(row.get("option_d", "")).strip(),
                    "correct_answer": str(row.get("correct_answer", "")).strip().upper(),
                    "explanation":    str(row.get("explanation", "")).strip() or None,
                    "source":         str(row.get("source", "Bulk Import")).strip(),
                }

            # Validate required fields
            row_errors = []
            if not q_dict["question_text"]:     row_errors.append("question text is empty")
            if not q_dict["option_a"]:          row_errors.append("option A is empty")
            if not q_dict["option_b"]:          row_errors.append("option B is empty")
            if not q_dict["option_c"]:          row_errors.append("option C is empty")
            if not q_dict["option_d"]:          row_errors.append("option D is empty")
            if q_dict["correct_answer"] not in ("A", "B", "C", "D"):
                row_errors.append(f"answer '{q_dict['correct_answer']}' is not A/B/C/D")
            if is_full_format and not q_dict["subject"]:
                row_errors.append("subject is empty")
            if is_full_format and not q_dict["topic"]:
                row_errors.append("topic is empty")

            if row_errors:
                validation_errors.append(f"Row {row_num}: {', '.join(row_errors)}")
            else:
                questions_to_import.append(q_dict)

        # Show validation summary
        valid_count   = len(questions_to_import)
        invalid_count = len(validation_errors)

        if invalid_count == 0:
            st.success(f"✅ All {valid_count} rows are valid and ready to import.")
        else:
            st.warning(f"⚠️ {valid_count} rows are valid. {invalid_count} rows have errors (shown below) and will be skipped.")
            with st.expander(f"Show {invalid_count} validation error(s)"):
                for err in validation_errors:
                    st.markdown(f"- {err}")

        # ── Import Button ─────────────────────
        if valid_count > 0:
            st.markdown("---")

            # For CBT Pro format, warn if metadata fields are not filled
            ready_to_import = True
            if is_cbt_format:
                if not bulk_topic.strip():
                    st.error("❌ Please fill in the Topic field before importing.")
                    ready_to_import = False

            if ready_to_import:
                if st.button(f"📥 Import {valid_count} Questions into Database", type="primary", use_container_width=True):
                    success_count, error_count, error_msgs = bulk_insert_questions(questions_to_import)

                    if error_count == 0:
                        st.success(f"🎉 Successfully imported {success_count} questions!")
                        st.balloons()
                    else:
                        st.warning(f"Imported {success_count} questions. {error_count} failed.")
                        for msg in error_msgs:
                            st.error(msg)

                    st.rerun()


# ─────────────────────────────────────────────
# PAGE 6 — EXPORT CSV
# ─────────────────────────────────────────────

elif page == "📤 Export CSV":
    st.title("📤 Export to CBT Pro CSV")
    st.markdown("Choose your filters, then download — ready to upload directly to CBT Pro.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        subject_filter = st.selectbox("Subject", ["All"] + get_subjects())
    with col2:
        class_filter = st.selectbox("Class Level", ["All"] + CLASS_LEVELS)

    df = get_questions(subject_filter=subject_filter, class_filter=class_filter)
    st.markdown(f"**{len(df)} question(s) match your filters.**")

    if df.empty:
        st.info("No questions to export. Adjust your filters or add questions first.")
    else:
        st.subheader("Preview (first 5 questions)")
        preview_cols = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]
        st.dataframe(df[preview_cols].head(5), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Build the CBT Pro CSV
        export_df = pd.DataFrame({
            "Question":    df["question_text"],
            "A":           df["option_a"],
            "B":           df["option_b"],
            "C":           df["option_c"],
            "D":           df["option_d"],
            "Answer":      df["correct_answer"],
            "Explanation": df["explanation"].fillna(""),
        })

        has_yoruba = "Yoruba" in df["subject"].values
        encoding   = "utf-8-sig" if has_yoruba else "utf-8"

        csv_buffer = io.BytesIO()
        export_df.to_csv(csv_buffer, index=False, encoding=encoding)
        csv_bytes = csv_buffer.getvalue()

        subject_label = subject_filter.replace(" ", "_") if subject_filter != "All" else "All_Subjects"
        class_label   = class_filter if class_filter != "All" else "All_Classes"
        filename = f"CBTPro_{subject_label}_{class_label}_{len(df)}questions.csv"

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
