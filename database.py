"""
database.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

This file handles ALL database operations.
The app.py file calls these functions — it never talks to SQLite directly.
This clean separation makes the code easier to maintain and upgrade.
"""

import sqlite3
import pandas as pd
from datetime import datetime

# The database file will be created in the same folder as app.py
DB_FILE = "question_bank.db"


def get_connection():
    """
    Opens a connection to the SQLite database.
    SQLite creates the file automatically if it does not exist yet.
    We set check_same_thread=False because Streamlit runs in multiple threads.
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This lets us access columns by name, not just index
    return conn


def initialise_database():
    """
    Creates the questions table if it does not already exist.
    Call this once when the app starts up.
    IF NOT EXISTS means it is safe to call every time — it will not wipe your data.
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
    Returns the ID of the newly created question (useful for confirmation messages).
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

    new_id = cursor.lastrowid  # SQLite tells us the ID it assigned
    conn.commit()
    conn.close()
    return new_id


def get_questions(subject_filter=None, class_filter=None):
    """
    Fetches questions from the database as a pandas DataFrame.

    - If no filters are given, returns ALL questions.
    - If subject_filter is provided, only returns that subject.
    - If class_filter is provided, only returns that class level.
    - Both filters can be combined.

    We use pandas DataFrame because Streamlit displays it beautifully
    and pandas makes CSV export trivial.
    """
    conn = get_connection()

    # Build the query dynamically based on which filters are active
    query = "SELECT * FROM questions WHERE 1=1"
    params = []

    if subject_filter and subject_filter != "All":
        query += " AND subject = ?"
        params.append(subject_filter)

    if class_filter and class_filter != "All":
        query += " AND class_level = ?"
        params.append(class_filter)

    query += " ORDER BY date_added DESC"  # Newest questions appear first

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def delete_question(question_id):
    """
    Permanently deletes a question by its ID.
    Returns True if a row was deleted, False if the ID was not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    rows_affected = cursor.rowcount  # 1 if deleted, 0 if ID not found

    conn.commit()
    conn.close()
    return rows_affected > 0


def get_subjects():
    """
    Returns a sorted list of all unique subjects currently in the database.
    Used to populate filter dropdowns dynamically.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject FROM questions ORDER BY subject")
    subjects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return subjects


def get_question_count():
    """
    Returns the total number of questions in the database.
    Used for the dashboard summary at the top of the app.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_count_by_subject():
    """
    Returns a DataFrame with question counts grouped by subject.
    Example: Mathematics | 45
             Physics      | 30
    Used for the mini dashboard display.
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
