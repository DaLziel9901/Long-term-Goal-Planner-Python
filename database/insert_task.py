import sqlite3
from get_connection import get_connection
from get_task_by_id import get_task_by_id

def insert_task(parent_id, title, description, start_date, end_date, is_done=0, is_random=0, order_index=0):
    connection = get_connection()
    cursor = connection.cursor()

    if parent_id is None:
        root_id = None
        level = 0
    else:
        parent = get_task_by_id(parent_id)
        root_id = parent['root_id']
        level = parent['level'] + 1

    cursor.execute("""
        INSERT INTO Task (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index))

    new_id = cursor.lastrowid
    if parent_id is None:
        cursor.execute("UPDATE Task SET root_id = ? WHERE id = ?", (new_id, new_id))

    connection.commit()
    connection.close()