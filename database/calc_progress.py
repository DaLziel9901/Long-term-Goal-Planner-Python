from database.get_connection import get_connection
from database.get_children import get_children

def calc_progress(task_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Task WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        connection.close()
        return 0.0  

    children = get_children(task_id)

    if not children:
        progress = 100.0 if task['is_done'] == 1 else 0.0
    else:
        total_progress = 0.0
        for child in children:
            child_progress = calc_progress(child['id'])
            total_progress += child_progress

        progress = total_progress / len(children)

    connection.close()
    return progress
