import os
import psycopg2
from dotenv import load_dotenv


def get_db_config():
    """Load database configuration from environment variables."""
    load_dotenv()
    return {
        'user': os.environ['USER'],
        'password': os.environ['PASSWORD'],
        'host': os.environ['HOST'],
        'database': os.environ['DATABASE']
    }


def with_cursor_connection(f):
    def wrapper(*args):
        config = get_db_config()
        connection = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=5432,
            database=config['database'],
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
        config = get_db_config()
        connection = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=5432,
            database=config['database'],
            options='-c search_path=stream_sniper'
        )
        cursor = connection.cursor()

        values = f(*args, cursor)
        cursor.close()
        connection.close()
        return values

    return wrapper
