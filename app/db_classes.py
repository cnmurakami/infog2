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
    
class Product():
    def __init__(self, id:int = -1, description:str = '', sell_value: float = -1, barcode:str = "", section_id: int = -1, stock: int = -1, expiration_date:str = ""):
        if barcode != '':
            query = """SELECT * FROM products WHERE barcode = %s limit 1"""
            arg = barcode
        elif id != -1:
            query = """SELECT * FROM products WHERE id = %s limit 1"""
            arg = id
        existing_product = db_operations.select(query, (arg,), 1)
        if existing_product==None:
            raise ObjectNotFound
        self.id = int(existing_product[0])
        self.description = existing_product[1]
        self.sell_value = existing_product[2]
        self.barcode = existing_product[3]
        self.section_id = existing_product[4]
        self.stock = existing_product[5]
        self.expiration_date = existing_product[6]
        return
