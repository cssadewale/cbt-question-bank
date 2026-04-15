"""
database.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1: get_connection, initialise_database, add_question, get_questions,
         delete_question, get_subjects, get_question_count, get_count_by_subject

Phase 2: search_questions, update_question, bulk_insert_questions

Phase 3: check_duplicates, get_random_questions,
         get_count_by_class, get_count_by_topic, get_count_by_source

Dynamic Subjects: add_subject, delete_subject
  - Subjects are now stored in a database table, not hardcoded in app.py
  - get_subjects() now reads from that table instead of a Python list
"""

import sqlite3
import pandas as pd

DB_FILE = "question_bank.db"

# These are the default subjects loaded into the database on first run.
# After first run, subjects live in the database — this list is never used again.
DEFAULT_SUBJECTS = [
    "Mathematics",
    "Further Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English Language",
    "Yoruba",
    "Economics",
    "Geography",
]


# ─────────────────────────────────────────────
# CONNECTION & INITIALISATION
# ─────────────────────────────────────────────

def get_connection():
    """
    Opens a connection to the SQLite database.
    check_same_thread=False is required for Streamlit's multi-thread environment.
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database():
    """
    Creates all tables if they do not already exist, and seeds default subjects.
    Safe to call every time the app starts — IF NOT EXISTS prevents data loss.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Main questions table — unchanged from previous phases
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

    # Subjects table — new.
    # Each subject name is stored as a unique row.
    # UNIQUE constraint means the same subject cannot be added twice.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            is_default INTEGER DEFAULT 0
        )
    """)

    # Seed default subjects if the table is empty.
    # INSERT OR IGNORE means: if the subject already exists, skip it silently.
    # This block runs on every app start but only does real work on the very first run.
    cursor.execute("SELECT COUNT(*) FROM subjects")
    count = cursor.fetchone()[0]

    if count == 0:
        for subject in DEFAULT_SUBJECTS:
            cursor.execute(
                "INSERT OR IGNORE INTO subjects (name, is_default) VALUES (?, 1)",
                (subject,)
            )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# SUBJECT MANAGEMENT (Dynamic Subjects)
# ─────────────────────────────────────────────

def get_subjects():
    """
    Returns a sorted list of all subject names from the subjects table.
    This replaces the old hardcoded SUBJECTS list in app.py.
    Any subject you add via add_subject() appears here immediately.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM subjects ORDER BY name")
    subjects = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return subjects


def add_subject(name):
    """
    Adds a new subject to the subjects table.
    Returns True if added successfully.
    Returns False if the subject already exists (UNIQUE constraint).

    We use INSERT OR IGNORE so SQLite handles the duplicate check for us —
    no need to query first then insert.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO subjects (name, is_default) VALUES (?, 0)",
        (name.strip(),)
    )

    # rowcount is 1 if a new row was inserted, 0 if it was ignored (duplicate)
    added = cursor.rowcount == 1
    conn.commit()
    conn.close()
    return added


def delete_subject(name):
    """
    Removes a subject from the subjects table.

    Safety check: we do NOT allow deletion if questions using that subject
    still exist in the questions table. This protects data integrity —
    you cannot orphan existing questions by deleting their subject.

    Returns:
        "deleted"     — subject was removed successfully
        "has_questions" — subject still has questions; cannot delete
        "not_found"   — subject name not in the table
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if any questions use this subject
    cursor.execute("SELECT COUNT(*) FROM questions WHERE subject = ?", (name,))
    question_count = cursor.fetchone()[0]

    if question_count > 0:
        conn.close()
        return "has_questions"

    cursor.execute("DELETE FROM subjects WHERE name = ?", (name,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()
    return "deleted" if deleted else "not_found"


def get_subject_details():
    """
    Returns a DataFrame of all subjects with their question counts.
    Used in the Manage Subjects page to show a full picture.

    We use a LEFT JOIN so subjects with zero questions still appear.
    Without LEFT JOIN, subjects with no questions would be invisible.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            s.name        AS subject,
            s.is_default  AS is_default,
            COUNT(q.id)   AS question_count
        FROM subjects s
        LEFT JOIN questions q ON q.subject = s.name
        GROUP BY s.name
        ORDER BY s.name
    """, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────
# PHASE 1 FUNCTIONS
# ─────────────────────────────────────────────

def add_question(subject, class_level, topic, subtopic, question_text,
                 option_a, option_b, option_c, option_d,
                 correct_answer, explanation, source):
    """Inserts one new question. Returns the new question's ID."""
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

    query  = "SELECT * FROM questions WHERE 1=1"
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
    """Permanently deletes a question by ID. Returns True if deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def get_question_count():
    """Returns the total number of questions in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_count_by_subject():
    """Returns a DataFrame: subject | question_count, sorted by count descending."""
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
# PHASE 2 FUNCTIONS
# ─────────────────────────────────────────────

def search_questions(query):
    """
    Full-text search across question_text, topic, subtopic, and explanation.
    Uses SQL LIKE with % wildcards — matches any question containing the term.
    """
    conn = get_connection()
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
    Updates every editable field of an existing question.
    id and date_added are never changed.
    Returns True if updated, False if ID not found.
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
    Inserts many questions in a single database transaction.
    Returns (success_count, error_count, error_messages).
    """
    conn = get_connection()
    cursor = conn.cursor()

    success_count  = 0
    error_count    = 0
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

        conn.commit()

    except Exception as e:
        conn.rollback()
        error_messages.append(f"Transaction failed: {str(e)}")

    finally:
        conn.close()

    return success_count, error_count, error_messages


# ─────────────────────────────────────────────
# PHASE 3 FUNCTIONS
# ─────────────────────────────────────────────

def check_duplicates(new_question_text, threshold=80):
    """
    Compares a new question against all existing questions using fuzzy matching.
    Returns a list of matches above the threshold, sorted by score descending.
    """
    from thefuzz import fuzz

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question_text, subject, class_level, topic FROM questions")
    all_questions = cursor.fetchall()
    conn.close()

    duplicates = []
    for row in all_questions:
        score = fuzz.token_sort_ratio(
            new_question_text.lower(),
            row["question_text"].lower()
        )
        if score >= threshold:
            duplicates.append({
                "id":               row["id"],
                "question_text":    row["question_text"],
                "subject":          row["subject"],
                "class_level":      row["class_level"],
                "topic":            row["topic"],
                "similarity_score": score,
            })

    duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return duplicates


def get_random_questions(subject, class_level, count):
    """
    Fetches `count` questions randomly using SQLite's ORDER BY RANDOM().
    Filters by subject and class_level if not "All".
    Returns a pandas DataFrame.
    """
    conn = get_connection()

    query  = "SELECT * FROM questions WHERE 1=1"
    params = []

    if subject != "All":
        query += " AND subject = ?"
        params.append(subject)

    if class_level != "All":
        query += " AND class_level = ?"
        params.append(class_level)

    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_count_by_class():
    """Returns a DataFrame: class_level | question_count."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT class_level, COUNT(*) as question_count
        FROM questions
        GROUP BY class_level
        ORDER BY class_level
    """, conn)
    conn.close()
    return df


def get_count_by_topic(limit=15):
    """Returns a DataFrame of the top `limit` topics by question count."""
    conn = get_connection()
    df = pd.read_sql_query(f"""
        SELECT topic, COUNT(*) as question_count
        FROM questions
        GROUP BY topic
        ORDER BY question_count DESC
        LIMIT {limit}
    """, conn)
    conn.close()
    return df


def get_count_by_source():
    """Returns a DataFrame: source | question_count, sorted descending."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT source, COUNT(*) as question_count
        FROM questions
        GROUP BY source
        ORDER BY question_count DESC
    """, conn)
    conn.close()
    return df
