import os
from typing import Callable

import psycopg2
from dotenv import load_dotenv


def get_db_config():
    """Load database configuration from environment variables."""
    load_dotenv()
    return {
        'user': os.environ['USER'],
        'password': os.environ['PASSWORD'],
        'host': os.environ['HOST'],
        'database': os.environ['DATABASE'],
        'port': int(os.environ.get('PORT', 5432))
    }


class DatabaseBuffer:
    def __init__(self, f: Callable, buffer_len: int = 7500):
        self.f = f
        self.buffer_len = buffer_len
        self.items = []
        config = get_db_config()
        self.connection = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            database=config['database'],
            options='-c search_path=stream_sniper'
        )

    def call_db_function(self):
        # don't continue, if there are no items to be inserted
        if not self.items:
            return

        cursor = self.connection.cursor()

        try:
            self.f(self.items, cursor, self.connection)
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            print(f"An error occurred: {e}")
        finally:
            self.items.clear()
            cursor.close()

    def add_item(self, item: tuple):
        self.items.append(item)

        if len(self.items) >= self.buffer_len:
            self.call_db_function()