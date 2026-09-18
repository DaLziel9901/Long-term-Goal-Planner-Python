from db_setup import get_connection
from get_task_by_id import get_task_by_id

def insert_task(parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index):
    connection = get_connection()
    cursor = connection.cursor()

    # If there is no parent_id -> main task, set root_id = None and level = 0
    if parent_id is None:
        root_id = None
        level = 0
    # If there is a parent_id -> subtask
    else:
        parent = get_task_by_id(parent_id) #todo
        root_id = parent['root_id']
        level = parent['level'] + 1

    cursor.execute("""
        INSERT INTO Task (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index))

    new_id = cursor.lastrowid
    if parent_id is None:
        # level 0 tasks have their own id as root_id
        cursor.execute("UPDATE Task SET root_id = ? WHERE id = ?", (new_id, new_id))
    
    connection.commit()
    connection.close()  