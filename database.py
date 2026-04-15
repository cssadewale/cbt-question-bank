"""
database.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1 functions: get_connection, initialise_database, add_question,
                   get_questions, delete_question, get_subjects,
                   get_question_count, get_count_by_subject

Phase 2 additions: search_questions, update_question, bulk_insert_questions
"""

import sqlite3
import pandas as pd

DB_FILE = "question_bank.db"


def get_connection():
    """
    Opens a connection to the SQLite database.
    SQLite creates the file automatically if it does not exist yet.
    check_same_thread=False is required for Streamlit's multi-thread environment.
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database():
    """
    Creates the questions table if it does not already exist.
    Safe to call every time the app starts — IF NOT EXISTS prevents data loss.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            subject         TEXT    NOT NULL,
            class_level     TEXT    NOT NULL,
            topic           TEXT    NOT NULL,
            subtopic        TEXT,
            question_text   TEXT    NOT NULL,
            option_a        TEXT    NOT NULL,
            option_b        TEXT    NOT NULL,
            option_c        TEXT    NOT NULL,
            option_d        TEXT    NOT NULL,
            correct_answer  TEXT    NOT NULL CHECK(correct_answer IN ('A','B','C','D')),
            explanation     TEXT,
            source          TEXT,
            date_added      TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()


def add_question(subject, class_level, topic, subtopic, question_text,
                 option_a, option_b, option_c, option_d,
                 correct_answer, explanation, source):
    """
    Inserts one new question into the database.
    Returns the ID of the newly created question.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO questions
            (subject, class_level, topic, subtopic, question_text,
             option_a, option_b, option_c, option_d,
             correct_answer, explanation, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (subject, class_level, topic, subtopic, question_text,
          option_a, option_b, option_c, option_d,
          correct_answer, explanation, source))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_questions(subject_filter=None, class_filter=None):
    """
    Fetches questions as a pandas DataFrame.
    Filters by subject and/or class level if provided.
    Returns newest questions first.
    """
    conn = get_connection()

    query = "SELECT * FROM questions WHERE 1=1"
    params = []

    if subject_filter and subject_filter != "All":
        query += " AND subject = ?"
        params.append(subject_filter)

    if class_filter and class_filter != "All":
        query += " AND class_level = ?"
        params.append(class_filter)

    query += " ORDER BY date_added DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def delete_question(question_id):
    """
    Permanently deletes a question by its ID.
    Returns True if deleted, False if ID was not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    rows_affected = cursor.rowcount

    conn.commit()
    conn.close()
    return rows_affected > 0


def get_subjects():
    """
    Returns a sorted list of all unique subjects in the database.
    Used to populate filter dropdowns dynamically.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject FROM questions ORDER BY subject")
    subjects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return subjects


def get_question_count():
    """Returns the total number of questions in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_count_by_subject():
    """
    Returns a DataFrame with question counts grouped by subject.
    Used for the dashboard bar chart.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT subject, COUNT(*) as question_count
        FROM questions
        GROUP BY subject
        ORDER BY question_count DESC
    """, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────
# PHASE 2 — NEW FUNCTIONS
# ─────────────────────────────────────────────

def search_questions(query):
    """
    PHASE 2 — Full-text search.

    Searches across question_text, topic, subtopic, and explanation.
    Uses SQL LIKE with % wildcards so it matches any question that
    CONTAINS the search term anywhere in those fields.

    Example: searching "quadratic" finds questions where the word
    "quadratic" appears in the question text OR topic OR subtopic.

    Returns a pandas DataFrame of matching questions.
    """
    conn = get_connection()

    # % wildcard means "any characters before or after the search term"
    search_term = f"%{query}%"

    df = pd.read_sql_query("""
        SELECT * FROM questions
        WHERE question_text LIKE ?
           OR topic         LIKE ?
           OR subtopic      LIKE ?
           OR explanation   LIKE ?
        ORDER BY date_added DESC
    """, conn, params=(search_term, search_term, search_term, search_term))

    conn.close()
    return df


def update_question(question_id, subject, class_level, topic, subtopic,
                    question_text, option_a, option_b, option_c, option_d,
                    correct_answer, explanation, source):
    """
    PHASE 2 — Edit an existing question.

    Updates every editable field for the question with the given question_id.
    The id and date_added columns are never changed — they stay permanent.

    Returns True if found and updated, False if the ID does not exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE questions
        SET subject        = ?,
            class_level    = ?,
            topic          = ?,
            subtopic       = ?,
            question_text  = ?,
            option_a       = ?,
            option_b       = ?,
            option_c       = ?,
            option_d       = ?,
            correct_answer = ?,
            explanation    = ?,
            source         = ?
        WHERE id = ?
    """, (subject, class_level, topic, subtopic, question_text,
          option_a, option_b, option_c, option_d,
          correct_answer, explanation, source,
          question_id))

    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def bulk_insert_questions(questions_list):
    """
    PHASE 2 — Bulk import multiple questions in one database transaction.

    questions_list is a Python list of dictionaries. Each dict must have:
        subject, class_level, topic, subtopic, question_text,
        option_a, option_b, option_c, option_d,
        correct_answer, explanation, source

    Why use a transaction?
    A transaction means all questions are saved together, or none at all.
    This protects your database from partial/corrupted imports.

    Returns a tuple: (success_count, error_count, error_messages)
    """
    conn = get_connection()
    cursor = conn.cursor()

    success_count = 0
    error_count = 0
    error_messages = []

    try:
        for i, q in enumerate(questions_list):
            try:
                cursor.execute("""
                    INSERT INTO questions
                        (subject, class_level, topic, subtopic, question_text,
                         option_a, option_b, option_c, option_d,
                         correct_answer, explanation, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    q.get("subject", ""),
                    q.get("class_level", ""),
                    q.get("topic", ""),
                    q.get("subtopic", None),
                    q.get("question_text", ""),
                    q.get("option_a", ""),
                    q.get("option_b", ""),
                    q.get("option_c", ""),
                    q.get("option_d", ""),
                    q.get("correct_answer", ""),
                    q.get("explanation", None),
                    q.get("source", "Bulk Import"),
                ))
                success_count += 1

            except Exception as e:
                error_count += 1
                error_messages.append(f"Row {i + 1}: {str(e)}")

        conn.commit()  # Save all successful inserts at once

    except Exception as e:
        conn.rollback()  # If transaction fails completely, undo everything
        error_messages.append(f"Transaction failed: {str(e)}")

    finally:
        conn.close()

    return success_count, error_count, error_messages
