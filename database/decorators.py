import os
import mariadb

USER = os.environ['USER']
PASSWORD = os.environ['PASS']
HOST = os.environ['HOST']
DATABASE = os.environ['DATABASE']


def with_cursor_connection(f):
    def wrapper(*args):
        connection = mariadb.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=3306,
            database=DATABASE
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
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=3306,
            database=DATABASE
        )
        cursor = connection.cursor()

        values = f(*args, cursor)
        cursor.close()
        connection.close()
        return values

    return wrapper
