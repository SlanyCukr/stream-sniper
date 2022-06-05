import mariadb


class DatabaseBuffer:
    def __init__(self, f, buffer_len=7500):
        self.f = f
        self.buffer_len = buffer_len
        self.items = []

    def call_db_function(self):
        connection = mariadb.connect(
            user="root",
            password="606361611Aa.",
            host="localhost",
            port=3306,
            database="stream_sniper"
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
