import os
from typing import Callable

import psycopg2

USER = os.environ['USER']
PASSWORD = os.environ['PASSWORD']
HOST = os.environ['HOST']
DATABASE = os.environ['DATABASE']
PORT = os.environ.get('PORT', 5432)  # Default PostgreSQL port is 5432


class DatabaseBuffer:
    def __init__(self, f: Callable, buffer_len: int = 7500):
        self.f = f
        self.buffer_len = buffer_len
        self.items = []
        self.connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            database=DATABASE,
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
            self.connection.close()

    def add_item(self, item: tuple):
        self.items.append(item)

        if len(self.items) >= self.buffer_len:
            self.call_db_function()