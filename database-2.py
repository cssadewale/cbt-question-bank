"""
database.py — CBT Question Bank Manager
Author: Adewale Samson Adeagbo

Phase 1: get_connection, initialise_database, add_question, get_questions,
         delete_question, get_subjects, get_question_count, get_count_by_subject

Phase 2: search_questions, update_question, bulk_insert_questions

Phase 3: check_duplicates, get_random_questions,
         get_count_by_class, get_count_by_topic, get_count_by_source
"""

import sqlite3
import pandas as pd

DB_FILE = "question_bank.db"


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
    Creates the questions table if it does not already exist.
    Safe to call every time the app starts.
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
    """Permanently deletes a question by ID. Returns True if deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def get_subjects():
    """Returns a sorted list of all unique subjects in the database."""
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
    PHASE 3 — Duplicate detection.

    Compares a new question against every existing question in the database
    using fuzzy string matching (thefuzz library).

    How fuzzy matching works:
    - It calculates how similar two strings are on a scale of 0 to 100
    - 100 = identical text
    - 80+ = very likely the same question, just worded slightly differently
    - 60-79 = similar but probably different questions
    - Below 60 = clearly different

    We use `fuzz.token_sort_ratio` which sorts the words alphabetically
    before comparing. This means "find the value of x if 2x=4" and
    "if 2x=4, find the value of x" score as near-identical even though
    the word order is different.

    Parameters:
        new_question_text : the question text you are about to save
        threshold         : minimum score to flag as a duplicate (default 80)

    Returns:
        A list of dicts, each with keys: id, question_text, subject,
        class_level, topic, similarity_score.
        Empty list means no duplicates found.
    """
    from thefuzz import fuzz  # Import here so the app still loads if library missing

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch only id, question_text, subject, class_level, topic — we do not
    # need all columns just to compare text
    cursor.execute("SELECT id, question_text, subject, class_level, topic FROM questions")
    all_questions = cursor.fetchall()
    conn.close()

    duplicates = []

    for row in all_questions:
        # token_sort_ratio is more reliable than plain ratio for question text
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

    # Sort by score descending so the closest match appears first
    duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return duplicates


def get_random_questions(subject, class_level, count):
    """
    PHASE 3 — Random exam generator.

    Fetches `count` questions randomly from the bank,
    filtered by subject and class_level.

    SQL's ORDER BY RANDOM() shuffles all matching rows and we take
    the first `count` using LIMIT. This is a true random selection —
    different every time you run it.

    Parameters:
        subject     : subject name string, or "All" for no filter
        class_level : class level string, or "All" for no filter
        count       : how many questions to return

    Returns a pandas DataFrame.
    Returns fewer rows than requested if the bank does not have enough
    questions matching the filters — the caller should check this.
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

    # ORDER BY RANDOM() is SQLite's built-in shuffle
    # LIMIT restricts to the requested number
    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_count_by_class():
    """
    PHASE 3 — Dashboard.
    Returns a DataFrame: class_level | question_count, ordered by class.
    """
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
    """
    PHASE 3 — Dashboard.
    Returns a DataFrame of the top `limit` topics by question count.
    We cap at 15 by default to keep the chart readable.
    """
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
    """
    PHASE 3 — Dashboard.
    Returns a DataFrame: source | question_count, sorted by count descending.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT source, COUNT(*) as question_count
        FROM questions
        GROUP BY source
        ORDER BY question_count DESC
    """, conn)
    conn.close()
    return df
