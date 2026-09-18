from db_setup import get_connection

def get_task_by_id(task_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Task WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    return dict(row) if row else None