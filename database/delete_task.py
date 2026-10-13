from contextlib import closing
from database.get_connection import get_connection


def delete_task(task_id):
    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM Task WHERE id = ?", (task_id,))
            if cursor.fetchone() is None:
                return 0

            def delete_recursive(current_id):
                cursor.execute(
                    "SELECT id FROM Task WHERE parent_id = ?",
                    (current_id,)
                )
                children = cursor.fetchall()

                # Xóa các con trước khi xóa cha.
                deleted_count = 0
                for child in children:
                    deleted_count += delete_recursive(child["id"])

                cursor.execute(
                    "DELETE FROM Task WHERE id = ?",
                    (current_id,)
                )
                return deleted_count + cursor.rowcount

            return delete_recursive(task_id)
