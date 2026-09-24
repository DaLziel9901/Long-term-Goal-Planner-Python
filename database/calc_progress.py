from get_connection import get_connection
from get_children import get_children

def calc_progress(task_id):
    connection = get_connection()
    cursor = connection.cursor()

    # Get the task by ID
    cursor.execute("SELECT * FROM Task WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    # No task found
    if not task:
        connection.close()
        return None  

    #Count all the children of the task
    children = get_children(task_id)

    if not children:
        # If there are no children, progress is 100% if the task is completed, otherwise 0%
        progress = 100.0 if task['is_done'] == 1 else 0.0
    else:
        # Calculate the average progress of all children
        total_progress = 0.0
        for child in children:
            child_progress = calc_progress(child['id'])
            total_progress += child_progress

        progress = total_progress / len(children)

    connection.close()
    return progress