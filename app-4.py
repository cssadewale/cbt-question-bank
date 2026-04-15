"""
app.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1: Add question, view/filter, delete, export CSV
Phase 2: Full-text search, edit question, bulk CSV import
Phase 3: Duplicate detection, rich dashboard, random exam generator
Dynamic Subjects: Manage subjects from inside the app — add and remove freely

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io

from database import (
    # Core
    initialise_database,
    add_question,
    get_questions,
    delete_question,
    get_question_count,
    get_count_by_subject,
    # Subjects — now dynamic
    get_subjects,
    add_subject,
    delete_subject,
    get_subject_details,
    # Phase 2
    search_questions,
    update_question,
    bulk_insert_questions,
    # Phase 3
    check_duplicates,
    get_random_questions,
    get_count_by_class,
    get_count_by_topic,
    get_count_by_source,
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
# Note: SUBJECTS is no longer a hardcoded list.
# We call get_subjects() wherever we need the subject list — it reads from the DB.
# ─────────────────────────────────────────────

CLASS_LEVELS   = ["JSS1", "JSS2", "JSS3", "SSS1", "SSS2", "SSS3"]
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
        "✏️ Edit Question",
        "📥 Bulk Import",
        "🎲 Exam Generator",
        "📤 Export CSV",
        "🗂️ Manage Subjects",   # New page
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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Total Questions", total)
    with col2:
        st.metric("📖 Subjects", len(get_subjects()))
    with col3:
        topic_df = get_count_by_topic(limit=100)
        st.metric("🏷️ Topics", len(topic_df))

    st.markdown("---")

    if total == 0:
        st.info("Your question bank is empty. Go to **➕ Add Question** to get started!")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("By Subject")
            subj_df = get_count_by_subject()
            st.bar_chart(subj_df.set_index("subject")["question_count"])
            st.dataframe(
                subj_df.rename(columns={"subject": "Subject", "question_count": "Questions"}),
                use_container_width=True, hide_index=True,
            )

        with col2:
            st.subheader("By Class Level")
            class_df = get_count_by_class()
            if not class_df.empty:
                st.bar_chart(class_df.set_index("class_level")["question_count"])
                st.dataframe(
                    class_df.rename(columns={"class_level": "Class", "question_count": "Questions"}),
                    use_container_width=True, hide_index=True,
                )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top 15 Topics")
            topic_df = get_count_by_topic(limit=15)
            if not topic_df.empty:
                st.bar_chart(topic_df.set_index("topic")["question_count"])
                st.dataframe(
                    topic_df.rename(columns={"topic": "Topic", "question_count": "Questions"}),
                    use_container_width=True, hide_index=True,
                )

        with col2:
            st.subheader("By Source")
            source_df = get_count_by_source()
            if not source_df.empty:
                st.bar_chart(source_df.set_index("source")["question_count"])
                st.dataframe(
                    source_df.rename(columns={"source": "Source", "question_count": "Questions"}),
                    use_container_width=True, hide_index=True,
                )

    st.markdown("---")
    st.markdown("""
    **Quick Guide:**
    - **➕ Add Question** — Enter a new question manually (with duplicate detection)
    - **🔍 View & Filter** — Browse, search, filter, and delete questions
    - **✏️ Edit Question** — Modify any existing question by ID
    - **📥 Bulk Import** — Upload a CSV file to import many questions at once
    - **🎲 Exam Generator** — Pick N random questions and export instantly
    - **📤 Export CSV** — Download filtered questions in CBT Pro format
    - **🗂️ Manage Subjects** — Add or remove subjects from your list
    """)


# ─────────────────────────────────────────────
# PAGE 2 — ADD QUESTION
# ─────────────────────────────────────────────

elif page == "➕ Add Question":
    st.title("➕ Add a New Question")
    st.markdown("Fill in all required fields (*) and click **Save Question**.")
    st.markdown("---")

    # Fetch subjects fresh from the database every time this page loads.
    # This means any subject you just added in Manage Subjects appears here immediately.
    subjects = get_subjects()

    if not subjects:
        st.warning("⚠️ No subjects found. Go to **🗂️ Manage Subjects** to add at least one subject first.")
        st.stop()

    # ── Duplicate Check ───────────────────────
    with st.expander("🔎 Check for duplicates before adding (optional)", expanded=False):
        st.markdown("Paste your question text to check if a similar one already exists. Score **80+** = likely duplicate.")
        check_text = st.text_area("Question text to check:", height=80, key="dup_check_text")
        check_threshold = st.slider("Sensitivity (80 = strict, 60 = loose):",
                                    min_value=50, max_value=95, value=80, step=5)

        if st.button("🔎 Check for Duplicates"):
            if not check_text.strip():
                st.warning("Please enter some question text to check.")
            elif total == 0:
                st.info("Your bank is empty — no duplicates possible yet.")
            else:
                with st.spinner("Scanning your question bank..."):
                    duplicates = check_duplicates(check_text.strip(), threshold=check_threshold)

                if duplicates:
                    st.warning(f"⚠️ Found {len(duplicates)} possible duplicate(s):")
                    for dup in duplicates:
                        st.markdown(
                            f"**ID {dup['id']}** — Score: `{dup['similarity_score']}%` | "
                            f"{dup['subject']} | {dup['class_level']} | {dup['topic']}"
                        )
                        st.markdown(f"> {dup['question_text']}")
                        st.markdown("---")
                else:
                    st.success("✅ No similar questions found. Safe to add!")

    st.markdown("---")

    with st.form("add_question_form", clear_on_submit=True):

        st.subheader("Question Classification")
        col1, col2 = st.columns(2)
        with col1:
            # Subjects come from the database — dynamic
            subject = st.selectbox("Subject *", subjects)
            topic   = st.text_input("Topic *", placeholder="e.g. Algebra, Organic Chemistry, Waves")
        with col2:
            class_level = st.selectbox("Class Level *", CLASS_LEVELS)
            subtopic    = st.text_input("Subtopic (optional)", placeholder="e.g. Quadratic Equations")

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
                auto_dups = check_duplicates(question_text.strip(), threshold=85)
                if auto_dups:
                    top = auto_dups[0]
                    st.warning(
                        f"⚠️ This question looks {top['similarity_score']}% similar to "
                        f"**Question #{top['id']}** already in your bank:\n\n"
                        f"> {top['question_text']}\n\n"
                        f"The question was still saved. Use **✏️ Edit** or **🗑️ Delete** if needed."
                    )

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
# PAGE 3 — VIEW & FILTER
# ─────────────────────────────────────────────

elif page == "🔍 View & Filter":
    st.title("🔍 View & Filter Questions")
    st.markdown("---")

    st.subheader("Search")
    search_query = st.text_input(
        "Search across all question text, topics, and explanations:",
        placeholder="e.g. quadratic, velocity, photosynthesis...",
    )

    st.markdown("---")
    st.subheader("Filter")
    col1, col2 = st.columns(2)
    with col1:
        subject_filter = st.selectbox("Filter by Subject", ["All"] + get_subjects())
    with col2:
        class_filter = st.selectbox("Filter by Class Level", ["All"] + CLASS_LEVELS)

    if search_query.strip():
        df = search_questions(search_query.strip())
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
        display_cols = ["id", "subject", "class_level", "topic", "question_text", "correct_answer", "source"]
        st.dataframe(
            df[display_cols].rename(columns={
                "id": "ID", "subject": "Subject", "class_level": "Class",
                "topic": "Topic", "question_text": "Question",
                "correct_answer": "Answer", "source": "Source",
            }),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.subheader("View Full Question Details")
        selected_id = st.selectbox("Select a Question ID to view in full:", df["id"].tolist())

        if selected_id:
            row = df[df["id"] == selected_id].iloc[0]
            with st.expander(f"Question #{selected_id} — Full Details", expanded=True):
                st.markdown(f"**Subject:** {row['subject']} | **Class:** {row['class_level']} | **Topic:** {row['topic']}")
                if pd.notna(row.get("subtopic")) and row.get("subtopic"):
                    st.markdown(f"**Subtopic:** {row['subtopic']}")
                st.markdown(f"**Question:** {row['question_text']}")
                st.markdown(f"- A: {row['option_a']}")
                st.markdown(f"- B: {row['option_b']}")
                st.markdown(f"- C: {row['option_c']}")
                st.markdown(f"- D: {row['option_d']}")
                st.markdown(f"**✅ Correct Answer:** {row['correct_answer']}")
                if pd.notna(row.get("explanation")) and row.get("explanation"):
                    st.markdown(f"**Explanation:** {row['explanation']}")
                st.markdown(f"**Source:** {row['source']} | **Date Added:** {row['date_added']}")
                st.info(f"To edit this question, go to **✏️ Edit Question** and enter ID **{selected_id}**.")

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
# PAGE 4 — EDIT QUESTION
# ─────────────────────────────────────────────

elif page == "✏️ Edit Question":
    st.title("✏️ Edit an Existing Question")
    st.markdown("Enter the Question ID to load it, make your changes, then save.")
    st.markdown("---")

    subjects    = get_subjects()
    edit_id     = st.number_input("Question ID to edit:", min_value=1, step=1, value=1)
    load_button = st.button("📂 Load Question")

    if load_button:
        all_questions = get_questions()
        match = all_questions[all_questions["id"] == edit_id]
        if match.empty:
            st.error(f"❌ No question found with ID {edit_id}.")
        else:
            st.session_state["edit_question"] = match.iloc[0].to_dict()
            st.success(f"✅ Question #{edit_id} loaded. Edit below and click Save.")

    if "edit_question" in st.session_state:
        q = st.session_state["edit_question"]

        # If the question's subject is not in the current subjects list
        # (e.g. it was added before a subject rename), add it temporarily
        # so the dropdown does not crash.
        edit_subjects = subjects if q["subject"] in subjects else [q["subject"]] + subjects

        st.markdown("---")
        st.markdown(f"**Editing Question ID: {q['id']}** | Originally added: {q['date_added']}")

        with st.form("edit_question_form"):
            st.subheader("Question Classification")
            col1, col2 = st.columns(2)
            with col1:
                subject = st.selectbox("Subject *", edit_subjects,
                    index=edit_subjects.index(q["subject"]))
                topic   = st.text_input("Topic *", value=q["topic"])
            with col2:
                class_level = st.selectbox("Class Level *", CLASS_LEVELS,
                    index=CLASS_LEVELS.index(q["class_level"]) if q["class_level"] in CLASS_LEVELS else 0)
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

            correct_answer = st.selectbox("Correct Answer *", ANSWER_OPTIONS,
                index=ANSWER_OPTIONS.index(q["correct_answer"]) if q["correct_answer"] in ANSWER_OPTIONS else 0)

            st.markdown("---")
            st.subheader("Additional Information")
            col1, col2 = st.columns(2)
            with col1:
                source = st.selectbox("Source", SOURCES,
                    index=SOURCES.index(q["source"]) if q["source"] in SOURCES else 0)

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
                        del st.session_state["edit_question"]
                        st.rerun()
                    else:
                        st.error("❌ Update failed. The question ID may no longer exist.")


# ─────────────────────────────────────────────
# PAGE 5 — BULK IMPORT
# ─────────────────────────────────────────────

elif page == "📥 Bulk Import":
    st.title("📥 Bulk Import from CSV")
    st.markdown("Upload a CSV file to import many questions at once.")
    st.markdown("---")

    subjects = get_subjects()

    with st.expander("📋 Accepted CSV Formats — click to expand", expanded=False):
        st.markdown("""
        **Format 1 — CBT Pro format:**
        ```
        Question,A,B,C,D,Answer,Explanation
        ```
        You fill in subject, class, topic, source once for the whole file.

        **Format 2 — Full format:**
        ```
        subject,class_level,topic,subtopic,question_text,option_a,option_b,option_c,option_d,correct_answer,explanation,source
        ```
        Each row carries its own metadata.
        """)

        template_cbt  = pd.DataFrame(columns=["Question", "A", "B", "C", "D", "Answer", "Explanation"])
        template_full = pd.DataFrame(columns=[
            "subject", "class_level", "topic", "subtopic",
            "question_text", "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "explanation", "source"
        ])

        col1, col2 = st.columns(2)
        with col1:
            st.download_button("⬇️ CBT Pro Template",
                template_cbt.to_csv(index=False), "template_cbt_pro_format.csv", "text/csv")
        with col2:
            st.download_button("⬇️ Full Format Template",
                template_full.to_csv(index=False), "template_full_format.csv", "text/csv")

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload your CSV file:", type=["csv"])

    if uploaded_file:
        try:
            try:
                raw_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                raw_df = pd.read_csv(uploaded_file, encoding="latin-1")
            st.success(f"✅ File read — {len(raw_df)} rows found.")
        except Exception as e:
            st.error(f"❌ Could not read the file: {e}")
            st.stop()

        columns_lower  = [c.lower().strip() for c in raw_df.columns]
        is_cbt_format  = "question" in columns_lower and "a" in columns_lower and "answer" in columns_lower
        is_full_format = "question_text" in columns_lower and "subject" in columns_lower

        if not is_cbt_format and not is_full_format:
            st.error("❌ Column headers not recognised. Download a template above.")
            st.stop()

        if is_cbt_format:
            st.info("📌 CBT Pro format detected. Fill in the metadata for all questions in this file.")
            col1, col2 = st.columns(2)
            with col1:
                bulk_subject = st.selectbox("Subject *", subjects, key="bulk_subject")
                bulk_topic   = st.text_input("Topic *", key="bulk_topic")
            with col2:
                bulk_class  = st.selectbox("Class Level *", CLASS_LEVELS, key="bulk_class")
                bulk_source = st.selectbox("Source", SOURCES, key="bulk_source")
            bulk_subtopic = st.text_input("Subtopic (optional)", key="bulk_subtopic")

        st.markdown("---")
        st.subheader(f"Preview — first 5 of {len(raw_df)} rows")
        st.dataframe(raw_df.head(5), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Validation")

        questions_to_import = []
        validation_errors   = []

        for i, row in raw_df.iterrows():
            row_num = i + 2

            if is_cbt_format:
                q_text = str(row.get("Question", "")).strip()
                opt_a  = str(row.get("A", "")).strip()
                opt_b  = str(row.get("B", "")).strip()
                opt_c  = str(row.get("C", "")).strip()
                opt_d  = str(row.get("D", "")).strip()
                answer = str(row.get("Answer", "")).strip().upper()
                expl   = str(row.get("Explanation", "")).strip()

                q_dict = {
                    "subject": bulk_subject, "class_level": bulk_class,
                    "topic": bulk_topic, "subtopic": bulk_subtopic or None,
                    "question_text": q_text,
                    "option_a": opt_a, "option_b": opt_b,
                    "option_c": opt_c, "option_d": opt_d,
                    "correct_answer": answer,
                    "explanation": expl if expl and expl.lower() != "nan" else None,
                    "source": bulk_source,
                }
            else:
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

            row_errors = []
            if not q_dict["question_text"]:  row_errors.append("question text is empty")
            if not q_dict["option_a"]:       row_errors.append("option A is empty")
            if not q_dict["option_b"]:       row_errors.append("option B is empty")
            if not q_dict["option_c"]:       row_errors.append("option C is empty")
            if not q_dict["option_d"]:       row_errors.append("option D is empty")
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

        valid_count   = len(questions_to_import)
        invalid_count = len(validation_errors)

        if invalid_count == 0:
            st.success(f"✅ All {valid_count} rows valid and ready to import.")
        else:
            st.warning(f"⚠️ {valid_count} rows valid. {invalid_count} rows have errors and will be skipped.")
            with st.expander(f"Show {invalid_count} error(s)"):
                for err in validation_errors:
                    st.markdown(f"- {err}")

        if valid_count > 0:
            st.markdown("---")
            ready = True
            if is_cbt_format and not bulk_topic.strip():
                st.error("❌ Please fill in the Topic field before importing.")
                ready = False

            if ready:
                if st.button(f"📥 Import {valid_count} Questions", type="primary", use_container_width=True):
                    success_count, error_count, error_msgs = bulk_insert_questions(questions_to_import)
                    if error_count == 0:
                        st.success(f"🎉 Successfully imported {success_count} questions!")
                        st.balloons()
                    else:
                        st.warning(f"Imported {success_count}. {error_count} failed.")
                        for msg in error_msgs:
                            st.error(msg)
                    st.rerun()


# ─────────────────────────────────────────────
# PAGE 6 — EXAM GENERATOR
# ─────────────────────────────────────────────

elif page == "🎲 Exam Generator":
    st.title("🎲 Random Exam Generator")
    st.markdown("Pick a subject, class level, and number of questions. The app selects randomly and exports instantly.")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        gen_subject = st.selectbox("Subject", ["All"] + get_subjects())
    with col2:
        gen_class   = st.selectbox("Class Level", ["All"] + CLASS_LEVELS)
    with col3:
        gen_count   = st.number_input("Number of Questions", min_value=1, max_value=200, value=40, step=5)

    st.markdown("---")

    available_df    = get_questions(
        subject_filter=gen_subject if gen_subject != "All" else None,
        class_filter=gen_class   if gen_class   != "All" else None,
    )
    available_count = len(available_df)

    if available_count == 0:
        st.warning("⚠️ No questions found for this selection.")
    else:
        st.info(f"**{available_count}** questions available. You requested **{gen_count}**.")

        if gen_count > available_count:
            st.warning(f"⚠️ Only {available_count} available — export will contain all {available_count}.")

        if st.button("🎲 Generate Random Exam", type="primary", use_container_width=True):
            exam_df = get_random_questions(subject=gen_subject, class_level=gen_class, count=gen_count)

            if exam_df.empty:
                st.error("❌ No questions returned. Try adjusting your filters.")
            else:
                actual_count = len(exam_df)
                st.success(f"✅ {actual_count} questions selected randomly!")

                preview_cols = ["id", "subject", "class_level", "topic", "question_text", "correct_answer"]
                st.dataframe(
                    exam_df[preview_cols].rename(columns={
                        "id": "ID", "subject": "Subject", "class_level": "Class",
                        "topic": "Topic", "question_text": "Question", "correct_answer": "Answer"
                    }),
                    use_container_width=True, hide_index=True,
                )

                export_df = pd.DataFrame({
                    "Question":    exam_df["question_text"],
                    "A":           exam_df["option_a"],
                    "B":           exam_df["option_b"],
                    "C":           exam_df["option_c"],
                    "D":           exam_df["option_d"],
                    "Answer":      exam_df["correct_answer"],
                    "Explanation": exam_df["explanation"].fillna(""),
                })

                has_yoruba = "Yoruba" in exam_df["subject"].values
                encoding   = "utf-8-sig" if has_yoruba else "utf-8"

                csv_buffer = io.BytesIO()
                export_df.to_csv(csv_buffer, index=False, encoding=encoding)

                subject_label = gen_subject.replace(" ", "_") if gen_subject != "All" else "Mixed"
                class_label   = gen_class if gen_class != "All" else "AllClasses"
                filename      = f"Exam_{subject_label}_{class_label}_{actual_count}q.csv"

                st.markdown("---")
                st.download_button(
                    label=f"⬇️ Download Exam CSV ({actual_count} questions)",
                    data=csv_buffer.getvalue(),
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True,
                )


# ─────────────────────────────────────────────
# PAGE 7 — EXPORT CSV
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
        st.dataframe(
            df[["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]].head(5),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")

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

        subject_label = subject_filter.replace(" ", "_") if subject_filter != "All" else "All_Subjects"
        class_label   = class_filter if class_filter != "All" else "All_Classes"
        filename      = f"CBTPro_{subject_label}_{class_label}_{len(df)}questions.csv"

        st.download_button(
            label=f"⬇️ Download {len(df)} Questions as CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.info(f"""
        **File details:**
        - Filename: `{filename}`
        - Encoding: `{encoding}` {'(UTF-8 with BOM for Yoruba)' if has_yoruba else '(standard UTF-8)'}
        - Questions included: {len(df)}
        """)


# ─────────────────────────────────────────────
# PAGE 8 — MANAGE SUBJECTS (New)
# ─────────────────────────────────────────────

elif page == "🗂️ Manage Subjects":
    st.title("🗂️ Manage Subjects")
    st.markdown("Add new subjects or remove ones you no longer need.")
    st.markdown("---")

    # ── Current Subjects Table ────────────────
    st.subheader("Current Subjects")
    details_df = get_subject_details()

    if details_df.empty:
        st.info("No subjects yet. Add one below.")
    else:
        # Show a clean table: subject name, question count, whether it is a default
        display_df = details_df.copy()
        display_df["Type"] = display_df["is_default"].apply(
            lambda x: "Default" if x == 1 else "Custom"
        )
        st.dataframe(
            display_df[["subject", "question_count", "Type"]].rename(columns={
                "subject": "Subject",
                "question_count": "Questions",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # ── Add a New Subject ─────────────────────
    st.subheader("➕ Add a New Subject")
    st.markdown("Type the exact name as you want it to appear in all dropdowns.")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_subject_name = st.text_input(
            "New subject name:",
            placeholder="e.g. Technical Drawing, Agricultural Science, Civic Education",
            label_visibility="collapsed",
        )
    with col2:
        add_button = st.button("➕ Add Subject", use_container_width=True)

    if add_button:
        if not new_subject_name.strip():
            st.error("❌ Please type a subject name before clicking Add.")
        else:
            added = add_subject(new_subject_name.strip())
            if added:
                st.success(f"✅ **{new_subject_name.strip()}** has been added to your subject list.")
                st.rerun()  # Refresh so the table and all dropdowns update immediately
            else:
                st.warning(f"⚠️ **{new_subject_name.strip()}** already exists in your subject list.")

    st.markdown("---")

    # ── Remove a Subject ──────────────────────
    st.subheader("🗑️ Remove a Subject")
    st.markdown("""
    You can only remove a subject if it has **zero questions** attached to it.
    This protects your existing questions from being orphaned.
    If the subject has questions, delete or reassign those questions first.
    """)

    all_subjects = get_subjects()
    if all_subjects:
        col1, col2 = st.columns([3, 1])
        with col1:
            subject_to_delete = st.selectbox(
                "Select subject to remove:",
                all_subjects,
                label_visibility="collapsed",
            )
        with col2:
            delete_button = st.button("🗑️ Remove", use_container_width=True, type="primary")

        if delete_button:
            result = delete_subject(subject_to_delete)

            if result == "deleted":
                st.success(f"✅ **{subject_to_delete}** has been removed.")
                st.rerun()
            elif result == "has_questions":
                # Count how many questions so the user knows the scale of work needed
                all_q = get_questions(subject_filter=subject_to_delete)
                st.error(
                    f"❌ Cannot remove **{subject_to_delete}** — it still has "
                    f"**{len(all_q)} question(s)** in your bank. "
                    f"Delete or edit those questions first, then try again."
                )
            elif result == "not_found":
                st.error(f"❌ Subject not found.")
    else:
        st.info("No subjects to remove.")
