import psycopg2

def postgres_connection():
    try:
        return psycopg2.connect(host = 'localhost', port = 5431, user = "admin", password = "admin", dbname = "infog2")
    except:
        return psycopg2.connect(host = 'db', port = 5432, user = "admin", password = "admin", dbname = "infog2")

def select(query:str, args:tuple = [], fetch = 0):
    db_connection = postgres_connection()
    db_cursor = db_connection.cursor()
    db_cursor.execute(query, args,)
    try:
        if fetch == 0:
            result = db_cursor.fetchall()
        elif fetch == 1:
            result = db_cursor.fetchone()
        else:
            result = db_cursor.fetchmany(fetch)
    except psycopg2.ProgrammingError:
        result = []
    db_cursor.close()
    db_connection.close()
    return result

def insert(query:str, args:tuple, return_field=''):
    if len(return_field) > 0:
        query += f"""RETURNING {return_field}"""
    db_connection = postgres_connection();
    db_cursor = db_connection.cursor()
    db_cursor.execute(query, args,)
    if len(return_field) > 0:
        result = db_cursor.fetchone()[0]
    else:
        result = []
    db_connection.commit()
    db_cursor.close()
    db_connection.close()
    return result
