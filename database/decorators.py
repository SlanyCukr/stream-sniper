import os
import mariadb

PASSWORD = os.environ['PASS']
HOST = os.environ['HOST']


def with_cursor_connection(f):
    def wrapper(*args):
        connection = mariadb.connect(
            user="stream_sniper",
            password=PASSWORD,
            host=HOST,
            port=3306,
            database="stream_sniper"
        )
        cursor = connection.cursor()

        values = f(*args, cursor, connection)
        cursor.close()
        connection.close()
        return values

    return wrapper


def with_cursor(f):
    def wrapper(*args):
        connection = mariadb.connect(
            user="stream_sniper",
            password=PASSWORD,
            host=HOST,
            port=3306,
            database="stream_sniper"
        )
        cursor = connection.cursor()

        values = f(*args, cursor)
        cursor.close()
        connection.close()
        return values

    return wrapper
