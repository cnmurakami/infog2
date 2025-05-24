import db_operations

class ObjectNotFound(Exception):
    pass

class User():
    def __init__(self, id:int = -1, username:str = '', password:str = "", role:int = -1, disabled:bool = False):
        if username != '':
            query = """SELECT * FROM users WHERE username = %s limit 1"""
            arg = username
        elif id != -1:
            query = """SELECT * FROM users WHERE id = %s limit 1"""
            arg = id
        existing_user = db_operations.select(query, (arg,), 1)
        if existing_user==None:
            raise ObjectNotFound
        self.id = int(existing_user[0])
        self.username = existing_user[1]
        self.password = existing_user[2]
        self.role = int(existing_user[3])
        self.disabled = bool(existing_user[4])
        return

class Client():
    def __init__(self, id:int = -1, name:str = '', email:str = "", cpf:str = ""):
        if cpf != '':
            query = """SELECT * FROM clients WHERE cpf = %s limit 1"""
            arg = cpf
        elif id != -1:
            query = """SELECT * FROM clients WHERE id = %s limit 1"""
            arg = id
        elif email != '':
            query = """SELECT * FROM clients WHERE email = %s limit 1"""
            arg = email
        existing_client = db_operations.select(query, (arg,), 1)
        if existing_client==None:
            raise ObjectNotFound
        self.id = int(existing_client[0])
        self.name = existing_client[1]
        self.email = existing_client[2]
        self.cpf = existing_client[3]
        return