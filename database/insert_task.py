from contextlib import closing
from database.get_connection import get_connection
from database.get_task_by_id import get_task_by_id

def insert_task(parent_id, title, description="", start_date=None, end_date=None,
                is_done=0, is_random=0, order_index=0):
    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.cursor()
            
            if parent_id is None:
                root_id = None
                level = 0
            else:
                parent = get_task_by_id(parent_id)
                if parent is None:
                    raise ValueError("Task cha không tồn tại")
                root_id = parent['root_id']
                level = parent['level'] + 1
        
            cursor.execute("""
                INSERT INTO Task (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (parent_id, root_id, level, title, description, start_date, end_date, is_done, is_random, order_index))
        
            new_id = cursor.lastrowid
            if parent_id is None:
                cursor.execute("UPDATE Task SET root_id = ? WHERE id = ?", (new_id, new_id))
        
            return new_id
            
