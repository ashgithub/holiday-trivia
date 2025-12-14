#!/usr/bin/env python3
"""
SQLite migration to remove the `hidden_prompt` column from the `questions` table.
Since SQLite does not support DROP COLUMN directly, we recreate the table
without the column and copy existing data.
"""

import sqlite3
import os
import sys

# Path to the SQLite database (project root)
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_game.db")

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not column_exists(cur, "questions", "hidden_prompt"):
        print("Column `hidden_prompt` does not exist – nothing to do.")
        conn.close()
        return

    # 1. Create new table without hidden_prompt
    cur.execute("""
        CREATE TABLE questions_new (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            answers TEXT,
            correct_answer TEXT NOT NULL,
            category TEXT NOT NULL,
            allow_multiple BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Copy data (ignore hidden_prompt)
    cur.execute("""
        INSERT INTO questions_new (id, type, content, answers, correct_answer, category, allow_multiple, created_at)
        SELECT id, type, content, answers, correct_answer, category, allow_multiple, created_at
        FROM questions
    """)

    # 3. Drop old table and rename new one
    cur.execute("DROP TABLE questions")
    cur.execute("ALTER TABLE questions_new RENAME TO questions")

    conn.commit()
    conn.close()
    print("Migration completed: `hidden_prompt` column removed from `questions` table.")

if __name__ == "__main__":
    main()
