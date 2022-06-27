import os
import mariadb

USER = os.environ['USER']
PASSWORD = os.environ['PASS']
HOST = os.environ['HOST']
DATABASE = os.environ['DATABASE']


class DatabaseBuffer:
    def __init__(self, f, buffer_len=7500):
        self.f = f
        self.buffer_len = buffer_len
        self.items = []

    def call_db_function(self):
        # don't continue, if there are no items to be inserted
        if not self.items:
            return

        connection = mariadb.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=3306,
            database=DATABASE
        )

        cursor = connection.cursor()

        self.f(self.items, cursor, connection)

        self.items.clear()
        cursor.close()
        connection.close()

    def add_item(self, item):
        self.items.append(item)

        if len(self.items) >= self.buffer_len:
            self.call_db_function()

    def delete_item(self, item):
        self.items.remove(item)
