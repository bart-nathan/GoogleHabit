import sqlite3
import os
from pathlib import Path

def get_file_name():
    src_db = Path(__file__).resolve().parent.parent / "habit.db"
    print(src_db)
    return str(src_db)

def get_db_connection():
    return sqlite3.connect(get_file_name())

def init_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Habits (
            habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_title TEXT NOT NULL,
            habit_description TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            habit_id INTEGER NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES Habits(habit_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

# Ensure tables are ready on module load
init_tables()

def exec_db(sql_statement, params=()):
    result = []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql_statement, params)

    if not sql_statement.strip().lower().startswith("select"):
        conn.commit()
    else:
        rs = cur.fetchall()
        for item in rs:
            result.append(item)

    conn.close()
    return result