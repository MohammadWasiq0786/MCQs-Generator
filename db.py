import sqlite3

DB_PATH = 'database/mcq.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mcqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            num_questions INTEGER,
            input_text TEXT,
            generated_mcqs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(filename, num_questions, input_text, generated_mcqs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO mcqs (filename, num_questions, input_text, generated_mcqs)
        VALUES (?, ?, ?, ?)
    """, (filename, num_questions, input_text, generated_mcqs))
    conn.commit()
    conn.close()
