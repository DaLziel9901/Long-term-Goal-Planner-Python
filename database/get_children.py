from get_connection import get_connection

def get_children(parent_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Task WHERE parent_id = ?", 
                   (parent_id,)
                   )

    rows = cursor.fetchall()
    connection.close()
    return [dict(row) for row in rows]