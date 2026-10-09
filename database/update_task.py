from get_connection import get_connection
from get_task_by_id import get_task_by_id


def update_task(task_id, title, description, start_date, end_date,
                is_done, order_index):


    task = get_task_by_id(task_id)

    if task is None:
        return False


    connection = get_connection()
    cursor = connection.cursor()


    cursor.execute("""
        UPDATE Task
        SET title = ?,
            description = ?,
            start_date = ?,
            end_date = ?,
            is_done = ?,
            order_index = ?
        WHERE id = ?
    """, (
        title,
        description,
        start_date,
        end_date,
        is_done,
        order_index,
        task_id
    ))


    connection.commit()


    connection.close()

    return True