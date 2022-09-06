import mysql.connector


class DbManager(object):
    def __init__(self, user, password, host, database):
        self.cnx = mysql.connector.connect(user=user, password=password, host=host, database=database)
        pass

    def execute(self, query):
        with self.cnx.cursor() as cursor:
            cursor.execute(query)
            results = [res for res in cursor]
        return results