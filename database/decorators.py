import os
import psycopg2

USER = os.environ['USER']
PASSWORD = os.environ['PASSWORD']
HOST = os.environ['HOST']
DATABASE = os.environ['DATABASE']


def with_cursor_connection(f):
    def wrapper(*args):
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=5432,
            database=DATABASE,
            options='-c search_path=stream_sniper'
        )
        cursor = connection.cursor()

        values = f(*args, cursor, connection)
        cursor.close()
        connection.close()
        return values

    return wrapper


def with_cursor(f):
    def wrapper(*args):
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=5432,
            database=DATABASE,
            options='-c search_path=stream_sniper'
        )
        cursor = connection.cursor()

        values = f(*args, cursor)
        cursor.close()
        connection.close()
        return values

    return wrapper
