import mysql.connector
from mysql.connector.errors import OperationalError

class DbManager(object):
    def __init__(self, user, password, host, database):
        self.user = user
        self.password = password
        self.host = host
        self.database = database
        self.cnx = mysql.connector.connect(user=user, password=password, host=host, database=database)

    def execute(self, query):
        try:
            with self.cnx.cursor() as cursor:
                cursor.execute(query)
                results = [res for res in cursor]
        except OperationalError:
            self.cnx = mysql.connector.connect(user=self.user, password=self.password, host=self.host, database=self.database)
            with self.cnx.cursor() as cursor:
                cursor.execute(query)
                results = [res for res in cursor]
        return results