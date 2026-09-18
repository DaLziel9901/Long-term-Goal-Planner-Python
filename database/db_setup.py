import sqlite3

def create_database():
    try:
        conn = sqlite3.connect("planner.db")
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            root_id INTEGER,
            level INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            is_done INTEGER DEFAULT 0,
            is_random INTEGER DEFAULT 0,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES Task(id),
            FOREIGN KEY (root_id) REFERENCES Task(id)
            );
        """)
        print("Database and Task table created successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred while creating the database: {e}")
    if conn:
        conn.commit()
        conn.close()

