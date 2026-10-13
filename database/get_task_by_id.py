from contextlib import closing
from database.get_connection import get_connection
def get_task_by_id(task_id):
    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM Task WHERE id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
