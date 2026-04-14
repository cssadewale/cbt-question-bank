# CBT Question Bank Manager
**Author:** Adewale Samson Adeagbo  
**Purpose:** Permanent, searchable database of exam questions with direct CBT Pro CSV export.

---

## Setup Instructions

### Running Locally (Primary Use)

1. Make sure Python is installed (3.9 or higher)
2. Install dependencies:
   ```
   pip install streamlit pandas
   ```
3. Run the app:
   ```
   streamlit run app.py
   ```
4. Open your browser to `http://localhost:8501`

The database file (`question_bank.db`) is created automatically on first run.

---

### Deploying to Streamlit Cloud (Demo Only)

> ⚠️ **Important:** SQLite resets on Streamlit Cloud every time the app restarts.  
> Use Streamlit Cloud only for demonstration. Your primary use should be local.

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo and select `app.py` as the main file
4. Deploy

---

## File Structure

```
cbt_question_bank/
├── app.py              ← Streamlit UI — all pages and forms
├── database.py         ← SQLite functions — all database logic
├── requirements.txt    ← Python packages needed
├── README.md           ← This file
└── question_bank.db    ← Auto-created on first run (do not delete!)
```

---

## CBT Pro Export Format

The exported CSV exactly matches the format required by CBT Pro:

```
"Question","A","B","C","D","Answer","Explanation"
"Find lim(x→2) (x²-4)/(x-2)","Undefined","4","2","0","B","Factor as (x-2)(x+2)..."
```

- Yoruba questions export with UTF-8-BOM encoding automatically
- Explanation column is included (blank if not provided)

---

## Phases

- ✅ **Phase 1 (current):** Add, view, filter, delete, export
- 🔜 **Phase 2:** Full text search, bulk CSV import, edit questions
- 🔜 **Phase 3:** Duplicate detection, dashboard charts, random exam generator
