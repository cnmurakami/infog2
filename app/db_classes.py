import db_operations
import base64

class ObjectNotFound(Exception):
    pass

class ItemNotFound(Exception):
    pass

class OrderCantBeChanged(Exception):
    pass

class User():
    def __init__(self, db_cursor = None, id:int = -1, username:str = '', password:str = "", role:int = -1, disabled:bool = False):
        if db_cursor == None:
            db_connection = db_operations.postgres_connection()
            db_cursor = db_connection.cursor()
        if username != '':
            query = """SELECT * FROM users WHERE username = %s limit 1"""
            arg = username
        elif id != -1:
            query = """SELECT * FROM users WHERE id = %s limit 1"""
            arg = id
        existing_user = db_operations.select(db_cursor, query, (arg,), 1)
        if existing_user==None:
            raise ObjectNotFound
        self.id = int(existing_user[0])
        self.username = existing_user[1]
        self.password = existing_user[2]
        self.role = int(existing_user[3])
        self.disabled = bool(existing_user[4])
        self.db_cursor = db_cursor
        return

class Client():
    def __init__(self, db_cursor = None, id:int = None, name:str = '', email:str = "", cpf:str = ""):
        if db_cursor == None:
            db_connection = db_operations.postgres_connection()
            db_cursor = db_connection.cursor()
        if cpf != '':
            query = """SELECT * FROM clients WHERE cpf = %s limit 1"""
            arg = cpf
        elif id != None:
            query = """SELECT * FROM clients WHERE id = %s limit 1"""
            arg = id
        elif email != '':
            query = """SELECT * FROM clients WHERE email = %s limit 1"""
            arg = email
        existing_client = db_operations.select(db_cursor, query, (arg,), 1)
        if existing_client==None:
            raise ObjectNotFound
        self.id = int(existing_client[0])
        self.name = existing_client[1]
        self.email = existing_client[2]
        self.cpf = existing_client[3]
        self.db_cursor = db_cursor
        return
    def get_info(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'cpf': self.cpf
        }
    
class Product():
    def __init__(self, db_cursor = None, id:int = None, description:str = '', sell_value: float = -1, barcode:str = "", section_id: int = -1, stock: int = -1, expiration_date:str = ""):
        if db_cursor == None:
            db_connection = db_operations.postgres_connection()
            db_cursor = db_connection.cursor()
        if id != None:
            query = """SELECT * FROM products WHERE id = %s limit 1"""
            arg = id
        else:
            query = """SELECT * FROM products WHERE barcode = %s limit 1"""
            arg = barcode
        existing_product = db_operations.select(db_cursor, query, (arg,), 1)
        if existing_product==None:
            raise ObjectNotFound
        self.id = int(existing_product[0])
        self.description = existing_product[1]
        self.sell_value = existing_product[2]
        self.barcode = existing_product[3]
        self.section_id = existing_product[4]
        self.stock = existing_product[5]
        self.expiration_date = existing_product[6]
        self.db_cursor = db_cursor
        return
    
    def get_info(self):
        return {
            'id': self.id,
            'description': self.description,
            'sell_value': self.sell_value,
            'barcode': self.barcode,
            'section_name': self.get_section_name(),
            'stock': self.stock,
            'expiration_date': self.expiration_date,
            'images': self.get_images()
        }
    def get_info_without_image(self):
        return {
            'id': self.id,
            'description': self.description,
            'sell_value': self.sell_value,
            'barcode': self.barcode,
            'section_name': self.get_section_name(),
            'stock': self.stock,
            'expiration_date': self.expiration_date,
        }
    
    def get_section_name(self):
        return db_operations.select(self.db_cursor, "SELECT name FROM sections where id = %s limit 1", (self.section_id,), 1)[0]

    def get_images(self) -> dict:
        '''
        Returns a dictionary with images from a specified product id.
        Raises ObjectNotFound if no image is found
        
        id:int: The product id to be looked for. 
        '''
        query = """
            SELECT image from images where product_id = %s
        """
        results_raw = db_operations.select(self.db_cursor, query, (self.id,))
        results = {}
        if len(results_raw) == 0:
            return results
        for i in range(len(results_raw)):
            results[i] = base64.b64encode(results_raw[i][0]).decode("utf-8")
        return results
    
    def insert_image(self, image:str):
        '''
            Saves an image in str format (from BASE64) into the image table
        '''
        if "," in image: # Remove header if any
            _, image = image.split(",", 1)
        image_bytes = base64.b64decode(image)
        bytea_hex = "\\x" + image_bytes.hex()
        result = db_operations.insert(self.db_cursor, "INSERT INTO images(product_id, image) values (%s, %s)", (self.id, bytea_hex), "id")
        return result



class Order():
    def __init__ (self, db_cursor = None, id:int = None):
        if db_cursor == None:
            db_connection = db_operations.postgres_connection()
            db_cursor = db_connection.cursor()
        existing_order = db_operations.select(db_cursor, "SELECT * FROM orders WHERE id = %s limit 1", (id,), 1)
        if existing_order == None:
            raise ObjectNotFound
        self.id = existing_order[0]
        self.created_at = existing_order[1]
        self.__status = existing_order[2]
        self.client_id = existing_order[3]
        self.db_cursor = db_cursor
    
    def get_info(self):
        return{
            'id': self.id,
            'client_id': self.client_id,
            'created_at': self.created_at,
            'status': self.get_status_description(self.__status),
            'products': self.get_products()
        }
    
    def get_status_description(self, status_id: str):
        try:
            description = db_operations.select(self.db_cursor, "SELECT description from order_status where id = %s LIMIT 1", (status_id,), 1)[0]
            return description
        except:
            raise ObjectNotFound

    def get_products(self):
        products = {}
        result_raw = db_operations.select(self.db_cursor, "SELECT * FROM orders_products WHERE order_id = %s", (self.id,))
        if result_raw == None or len(result_raw) == 0:
            return products
        for i in range(len(result_raw)):
            product = Product(self.db_cursor, id = result_raw[i][2])
            products[i+1] = product.get_info_without_image()
            products[i+1]['quantity'] = result_raw[i][3]
        return products

    def include_product(self, product_id:int, quantity: int) -> int:
        if self.__status == 1 or self.__status == 5:
            raise OrderCantBeChanged
        product = Product(self.db_cursor, product_id)
        if quantity > product.stock:
            raise ValueError
        
        product_list = self.get_products()
        product_in_order = None
        for item in product_list:
            if product_list[item]['id'] == product.id:
                product_in_order = product_list[item]
                break
        if product_in_order == None:
            result = db_operations.insert(self.db_cursor, 
                "INSERT INTO orders_products (order_id, product_id, quantity) VALUES (%s, %s, %s)",
                (self.id, product_id, quantity),
                'id'
            )
        else:
            result = db_operations.insert(self.db_cursor, 
                "UPDATE orders_products SET quantity = quantity + %s WHERE order_id = %s AND product_id = %s",
                (quantity, self.id, product_in_order['id'],)
            )
        if result == None:
            raise ObjectNotFound
        result = db_operations.insert(self.db_cursor, 
            "UPDATE products SET stock = stock-%s WHERE id = %s",
            (quantity, product.id, ),
            'stock'
        )
        return result
    
    def remove_product(self, product_id:int, quantity: int) -> int:
        if self.__status == 1 or self.__status == 5:
            raise OrderCantBeChanged
        product = Product(self.db_cursor, product_id)
        product_list = self.get_products()
        product_in_order = None
        for item in product_list:
            if product_list[item]['id'] == product.id:
                product_in_order = product_list[item]
                break
        if product_in_order == None:
            raise ItemNotFound
        if quantity > product_in_order['quantity']:
            raise ValueError
        elif quantity == product_in_order['quantity']:
            result = db_operations.insert(self.db_cursor, 
                "DELETE FROM orders_products WHERE order_id = %s AND product_id = %s",
                (self.id, product_in_order['id'],)
            )
        else:
            result = db_operations.insert(self.db_cursor, 
                "UPDATE orders_products SET quantity = quantity - %s WHERE order_id = %s AND product_id = %s",
                (quantity, self.id, product_in_order['id'],)
            )
        if result == None:
            raise ObjectNotFound
        result = db_operations.insert(self.db_cursor, 
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (quantity, product_in_order['id'], ),
            'stock'
        )
        return result
    
    def cancel_order(self):
        if self.__status == 1 or self.__status == 5:
            raise OrderCantBeChanged
        product_list = self.get_products()
        product_in_order = None
        for item in product_list:
            result = db_operations.insert(self.db_cursor, 
                "UPDATE products SET stock = stock + %s WHERE id = %s",
                (product_list[item]['quantity'], product_list[item]['id'],),
                'stock'
            )
        self.__status = 1

        result = db_operations.insert(self.db_cursor, 
            "UPDATE orders SET status = %s WHERE id = %s",
            (1, self.id,), "status"
        )
        if result == None:
            raise ObjectNotFound
        return
    
    def change_status(self, new_status):
        if self.__status == 1 or self.__status == 5:
            raise OrderCantBeChanged
        self.__status = new_status
        result = db_operations.insert(self.db_cursor, 
            "UPDATE orders SET status = %s WHERE id = %s",
            (new_status, self.id),
            "status"
        )
    def is_open(self):
        return not (self.__status == 1 or self.__status == 5)