from contextlib import closing
from database.get_connection import get_connection


def get_children(parent_id):
    with closing(get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM Task
            WHERE parent_id IS ?
            ORDER BY order_index ASC, id ASC
        """, (parent_id,))
        return [dict(row) for row in cursor.fetchall()]