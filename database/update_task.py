from contextlib import closing
from database.get_connection import get_connection

def update_task(task_id, title = None, description = None, start_date = None, end_date = None,
                is_done = None, order_index = None):

    if all(value is None for value in (
            title, description, start_date, end_date, is_done, order_index
        )):
            return False

    with closing(get_connection()) as connection:
            with connection:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM Task WHERE id = ?", (task_id,))
                task = cursor.fetchone()
    
                if task is None:
                    return False
    
                title = task["title"] if title is None else title
                description = task["description"] if description is None else description
                start_date = task["start_date"] if start_date is None else start_date
                end_date = task["end_date"] if end_date is None else end_date
                is_done = task["is_done"] if is_done is None else is_done
                order_index = task["order_index"] if order_index is None else order_index
    
                cursor.execute("""
                    UPDATE Task
                    SET title = ?, description = ?, start_date = ?,
                        end_date = ?, is_done = ?, order_index = ?
                    WHERE id = ?
                """, (title, description, start_date, end_date,
                      is_done, order_index, task_id))
    
                return True