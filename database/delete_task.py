from get_connection import get_connection


def delete_task(task_id):
    connection = get_connection()
    cursor = connection.cursor()

    def delete_recursive(id):

        cursor.execute(
            "SELECT id FROM Task WHERE parent_id = ?",
            (id,)
        )

        children = cursor.fetchall()


        for child in children:
            delete_recursive(child["id"])


        cursor.execute(
            "DELETE FROM Task WHERE id = ?",
            (id,)
        )

    delete_recursive(task_id)

    connection.commit()
    connection.close()