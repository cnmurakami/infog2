import psycopg2

def postgres_connection():
    try:
        return psycopg2.connect(host = 'localhost', port = 5431, user = "admin", password = "admin", dbname = "infog2")
    except:
        return psycopg2.connect(host = 'db', port = 5432, user = "admin", password = "admin", dbname = "infog2")

def select(db_cursor, query:str, args:tuple = [], fetch = 0):
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
    return result

def insert(cursor, query:str, args:tuple, return_field=''):
    if len(return_field) > 0:
        query += f""" RETURNING {return_field}"""
    cursor.execute(query, args,)
    if len(return_field) > 0:
        result = cursor.fetchone()[0]
    else:
        result = []
    
    return result
