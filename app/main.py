from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import re
import pytz

from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

import db_operations
import utils
from base_models import Token, User, NewUser, NewClient, UpdateClient, NewProduct, UpdateProduct, NewOrder, UpdateOrder
from db_classes import ObjectNotFound, ItemNotFound, OrderCantBeChanged, Client, Product, Order

app = FastAPI()

admin_role_id = 1

@app.get("/")
def index():
    return {"message":"Lu Estilo"}


# USER ROUTES ------------------------------------------------------------------------------------------------


@app.post("/auth/register")
async def register_user(
    form_data: NewUser,
    current_user: Optional[User] = Depends(utils.get_current_user_optional)
) -> dict:
    ''' Registers new user. Returns a success message and the ID of the new user.
    
    Both username and password must not be empty.
    
    Include optional "role" key to specify the role id. If not specified, defaults to lowest role.
    
    Role ID must exist in role table and current user must be already authenticated in the same role or higher (note that roles IDs are opposite to role, lower ID means higher role).

        username (str): The registering user username.
        username (password): The registering user password.
        role (int, optional, defaults to lowest role): The registering user role.
    
        Example request:
            {
                "username": "a_new_username",
                "password": "a_new_password",
                "role": 1
            }
        
        Example return:
            {
                "message": "Usuário cadastrado com sucesso",
                "id": 10
            }
    '''
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail= "Usuário e/ou senha em branco")
    try:
        utils.get_user(form_data.username)
        raise HTTPException(status_code=400, detail= "Usuário já existe")
    except ObjectNotFound:
        encrypted_password = utils.get_password_hash(form_data.password)
        query = """SELECT id from roles ORDER BY id DESC LIMIT 1"""
        lowest_role_id = db_operations.select(query=query, fetch=1)[0]
        if form_data.role:
            if not current_user:
                raise HTTPException(status_code=403, detail= "Precisa estar logado para definir permissão")
            if form_data.role < 1 or form_data.role > lowest_role_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Permissão fornecida não existe")
            if form_data.role < current_user.role:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Sem autorização para criar usuário com as permissões fornecidas")
            query = """INSERT INTO users (username, password_hash, role_id) VALUES(%s, %s, %s)"""
            result = db_operations.insert(query, (form_data.username, encrypted_password, form_data.role, ), "id")
        else:
            query = """INSERT INTO users (username, password_hash) VALUES(%s, %s)"""
            result = db_operations.insert(query, (form_data.username, encrypted_password,), "id")
        return {"message": "Usuário cadastrado com sucesso", "id": result}


@app.post("/token")
@app.post("/auth/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    ''' Route for login. Requires credentials following FastAPI documentation. Username and password must be stored in database to be authenticated.
    Returns access token if authenticated.
    Returns HTTPException with status code 401 otherwise.

        username (str): username to log in.
        password (str): user's password to log in.

        Example request:
            {
                "username": "a_valid_username",
                "password": "a_valid_password"
            }
    '''
    try:
        user = utils.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise ObjectNotFound
    except ObjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    sql_timestamp_string = datetime.fromtimestamp((datetime.now(timezone.utc)+access_token_expires).replace(tzinfo=None).timestamp())
    db_operations.insert("INSERT INTO tokens (user_id, token, expire_at) VALUES (%s, %s, %s);",
                         (user.id, access_token, sql_timestamp_string,))
    return Token(access_token=access_token, token_type="bearer")


@app.post("/auth/refresh-token")
async def refresh_access_token(
    current_user: Annotated[User, Depends(utils.get_current_active_user)]
) -> Token:
    ''' Generates a new token for the user as long as it's currently active
        Gets current token and returns a new one.
    '''
    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    sql_timestamp_string = datetime.fromtimestamp((datetime.now(timezone.utc)+access_token_expires).replace(tzinfo=None).timestamp())
    db_operations.insert("INSERT INTO tokens (user_id, token, expire_at) VALUES (%s, %s, %s);",
                         (current_user.id, access_token, sql_timestamp_string,))
    return Token(access_token=access_token, token_type="bearer")


# CLIENTS ROUTES ------------------------------------------------------------------------------------------------


@app.get("/clients")
async def get_clients(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    offset: Optional[int] = Query(0, ge=0),
    filter: Optional[str] = Query(None),
):
    '''
    Returns client list, limit of 20 entries.
    
        offset: (int, optional, default = 0) Sets the offset for the resulting list.
        filter: (str, optional, default = None) Filter results by name and email using the specified keyword.

        Example parameters:
            offset: 10
            filter: "an user first name"

        Example return:
            [
                {
                    'id': 10,
                    'name': "Jeoffrey Joey",
                    'email': "super_creative_email@aol.com",
                    'cpf': "20987654321"
                },
                {
                    'id': 11,
                    'name': "Katerine Kurva",
                    'email': "awesome_myself@live.com",
                    'cpf': "34567890123"
                }
            ]
    '''
    additional_string = ''
    if filter != None and filter != '':
        filter = '%'+filter.lower()+'%'
        additional_string = "WHERE name ILIKE %s OR email ILIKE %s"
        args = (filter, filter, offset,)
    else:
        args = (offset,)
    query = f"""SELECT id FROM clients {additional_string} LIMIT 20 OFFSET %s"""
    result_raw = db_operations.select(query, args)
    if len(result_raw) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    result = []
    for entry in result_raw:
        client = Client(entry[0])
        result.append(client.get_info())
    return result

@app.post("/clients")
async def create_client(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_client: NewClient
):
    """ Registers new client.  Returns a success message and the ID of the new client.
    
    All three request values are required. Email and CPF must be valid and unique.

        name (str): Client's name.
        email (str): Client's email (must be valid and unique).
        cpf (str): Client's cpf (numbers only, must be valid and unique).

        Example request:
            {
                "name": "a_valid_name",
                "email": "a_valid_and_unique_email",
                "cpf": "a_valid_and_unique_cpf"
            }
        
        Example return:
            {
                "message": "Cliente cadastrado com sucesso",
                "id": 10
            }
    """
    if len(new_client.name) < 1:
        raise HTTPException(status_code=400, detail= "Nome não pode ser vazio")
    if not utils.validate_cpf(new_client.cpf):
        raise HTTPException(status_code=400, detail= "CPF inválido")
    if not utils.validate_email(new_client.email):
        raise HTTPException(status_code=400, detail= "E-mail inválido")
    try:
        utils.get_client(new_client.cpf)
        raise HTTPException(status_code=400, detail= "CPF já existe")
    except ObjectNotFound:
        pass
    try: 
        utils.get_client(new_client.email)
        raise HTTPException(status_code=400, detail= "Email já existe")
    except ObjectNotFound:
        query = """
            INSERT INTO clients (name, email, cpf)
            VALUES (%s, %s, %s)
        """
        args = (new_client.name, new_client.email, new_client.cpf,)
        result = db_operations.insert(query, args, 'id')
        return {"message": "Cliente cadastrado com sucesso", "id": result}

@app.get("/clients/{id}")
async def get_client_by_id(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    ''' Returns a client properties identified by id.

    Returns 400 if no client is found.

        id: ID of the client to searched

        Example return:
            {
                'id': 10,
                'name': "Jeoffrey Joey",
                'email': "super_creative_email@aol.com",
                'cpf': "20987654321"
            }
    '''
    try:
        return Client(id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado")
    
@app.put("/clients/{id}")
async def put_client(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_information: UpdateClient
):
    ''' Updates a client by id. Only admins can update clients.
    
    If successful, returns the updated properties of the client.
    
    Returns 204 if no client is found.
    
    Accepts new name, cpf and email. At least one is required.

        name (str, default = None): Client's new name.
        email (str, default = None): Client's new email (must be valid and unique).
        cpf (str, default = None): Client's new cpf (numbers only, must be valid and unique. Do not include CPF if it's the same registered).

        Example request:
            {
                "name": "a_valid_new_name",
                "email": "a_valid_and_unique_new_email",
                "cpf": "a_valid_and_unique_new_cpf"
            }

        Example return:
            {
                "message": "Cliente atualizado com sucesso",
                "detail": {
                    "id": 10,
                    "nome": "Anna Kendrick",
                    "email": "my_only_email@me.com",
                    "cpf": "12345678901"
                }
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem editar clientes")
    if new_information.cpf == None and new_information.name == None and new_information.email == None:
        raise HTTPException(status_code=400, detail= "Necessita de ao menos uma informação para atualizar")
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
        client = Client(id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    
    values = []
    name_field = ''
    cpf_field = ''
    email_field = ''
    if new_information.name != None:
        if new_information.name == '':
            raise HTTPException(status_code=400, detail= "Nome inválido")
        name_field = 'name = %s,'
        values.append(new_information.name)
    if new_information.cpf != None:
        if not utils.validate_cpf(new_information.cpf):
            raise HTTPException(status_code=400, detail= "CPF inválido")
        try:
            utils.get_client(new_information.cpf)
            raise HTTPException(status_code=400, detail= "CPF já existe")
        except ObjectNotFound:
            cpf_field = 'cpf = %s,'
            values.append(new_information.cpf)
    if new_information.email != None:
        if not utils.validate_email(new_information.email):
            raise HTTPException(status_code=400, detail= "E-mail inválido")
        try:
            utils.get_client(new_information.email)
            raise HTTPException(status_code=400, detail= "E-mail já existe")
        except ObjectNotFound:
            email_field = 'email = %s,'
            values.append(new_information.email)
    query = f"""UPDATE clients SET {name_field} {cpf_field} {email_field} where id = %s """
    query = re.sub(' +', ' ', query)
    query = query.replace(", where", " where")
    values.append(id)
    result = db_operations.insert(query, values, "id")
    updated_client = Client(id = result)
    return {
        "message": "Cliente atualizado com sucesso",
        "detail": updated_client.get_info()
    }

@app.delete("/clients/{id}")
async def delete_client(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Deletes client from provided ID. Only admins can perform this action.
    
    If successful, returns success message.
    
    If client is not found, returns 204.

        id: ID of the client to be deleted

        Example return:
            {
                "message": "Cliente deletado com sucesso"
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem deletar clientes")
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
        client = Client(id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    query = """
        DELETE FROM clients WHERE id = %s
    """
    result = db_operations.insert(query, (id,))
    return {"message": "Cliente deletado com sucesso"}


# PRODUCTS ROUTES ------------------------------------------------------------------------------------------------

@app.get("/products")
async def get_products(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    offset: Optional[int] = Query(0, ge=0),
    category: Optional[str] = Query(None),
    sell_value: Optional[float] = Query(0, ge=0),
    available: Optional[bool] = Query(False)
):
    '''Returns products list, limit of 20 entries.
    
        offset (int, optional, default = 0): Sets the offset for the resulting list.
        category (str, optional, default = None): Filter results by section.
        sell_value (float, optional, default = 0): Filter results lower than the specified sell_value if > 0.
        available (bool, optional, default = False): Filter only results with items in stock if True

        Example parameters:
            offset: 10
            category: "Hortifruti"
            sell_value: 10.5
            available: True

        Example return:
            [
                {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                },
                {
                    "id": 4,
                    "description": "Óleo de Soja",
                    "sell_value": 6.9,
                    "barcode": "789100000004",
                    "section_name": "Marcearia",
                    "stock": 120,
                    "expiration_date": "2026-10-06",
                    "images": {
                        "0": "UklGRu..."
                    }
                }
            ]
    '''
    args = []
    category_string = ''
    sell_value_string = ''
    available_string = ''
    if category != None and category != '':
        try:
            category_id = utils.get_section_id(category)
            category_string = "section_id = %s AND "
            args.append(category_id)
        except ObjectNotFound:
            raise HTTPException(status_code=400, detail= "Categoria não localizada, por favor redefina o filtro")
    
    if sell_value > 0:
        sell_value_string = "sell_value <= %s AND "
        args.append(sell_value)

    if available:
        available_string = "stock > 0 AND "
    
    args.append(offset)
    query = f"""
        SELECT * FROM products {category_string}{sell_value_string}{available_string} LIMIT 20 OFFSET %s
    """
    query = re.sub(' +', ' ', query)
    query = query.replace(" AND LIMIT", " LIMIT")
    if len(category_string+sell_value_string+available_string)>0:
        query = query.replace("FROM products", "FROM products WHERE")
    result_raw = db_operations.select(query, args)
    if len(result_raw) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    result = []
    for entry in result_raw:
        product = Product(entry[0])
        result.append(product.get_info())
    return result

@app.post("/products")
async def create_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_product: NewProduct
):
    """ Registers new product. Returns a success message and the ID of the new product.

    Only admins can create products.

    All request fields are required, except for expiration_date and images.

        description (str): Product's description        
        sell_value (float): Product's selling value        
        barcode (str): Product's barcode, must be unique        
        section_id (int): ID of the product's section/category        
        stock (int): Initial stock of the product (must be greater than 0)        
        expiration_date (str, optional, default = None): Products expiration date in format dd/mm/aaaa
        images (list:str, optional, default = None) A list of the product images. Images must be a string in BASE64 encoded format. Headers are optional

        Example request:
                {
                    "description": "A product name/description",
                    "sell_value": 10.50,
                    "barcode": "000000000000000000001",
                    "section_id": 5,
                    "stock": 10,
                    "expiration_date": "01/01/1964"
                    "images": ["UklGRkB7AABXRUJQVlA4IDR7AABw6AOdASqwB...", "UklGRuCRAABXRUJQVlA4INSRA..."]
                }
        Example return:
            {
                "message": "Produto cadastrado com sucesso",
                "detail": {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                }
            }
    """
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem adicionar produtos")
    if new_product.sell_value < .01:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Preço de venda inválido")
    if new_product.stock < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Estoque inicial inválido")
    if new_product.expiration_date != None:
        try:
            date_obj = datetime.strptime(new_product.expiration_date, "%d/%m/%Y")
            new_product.expiration_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Prazo de validade inválido")
    try:
        query = "SELECT id FROM sections where id=%s"
        result = db_operations.select(query, (new_product.section_id,))
        if len(result) < 1:
            raise ObjectNotFound
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "ID de categoria inválido")
    try:
        existing_product = Product(barcode=new_product.barcode)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Código de barras já existe") 
    except ObjectNotFound:
        query = """
                INSERT INTO products (description, sell_value, barcode, section_id, stock, expiration_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
        args = (
            new_product.description,
            new_product.sell_value,
            new_product.barcode,
            new_product.section_id,
            new_product.stock,
            new_product.expiration_date,
        )
        result = db_operations.insert(query, args, 'id')
        saved_product = Product(result)
        message = "Produto cadastrado com sucesso"
        errored_image = False
        if new_product.images!=None:
            for image in new_product.images:
                try:
                    saved_product.insert_image(image)
                except:
                    if not errored_image:
                        message += ". Uma ou mais imagem não pôde ser salva..."
                        errored_image = True
        return {
            "message": message,
            "details": saved_product.get_info()
            }

@app.get("/products/{id}")
async def get_produc_by_id(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    ''' Returns a product properties identified by id.

    Returns 204 if no product is found.

        id: ID of the product to be searched
        
        Example return:
            {
                "id": 3,
                "description": "Feijão Carioca",
                "sell_value": 8.7,
                "barcode": "789100000003",
                "section_name": "Marcearia",
                "stock": 150,
                "expiration_date": "2025-06-12",
                "images": {
                    "0": "UklGRs..."
                    "1": "UKlGRo..."
                }
            }
    '''
    try:
        return Product(id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Produto não localizado")
    
@app.put("/products/{id}")
async def put_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_information: UpdateProduct
):
    ''' Updates a product by id. Only admins can update products.
    
    If successful, returns the updated properties of the product.
    
    Returns 204 if no product is found.
    
    Accepts any property of products to update, except ID which cannot be changed.
    
    All request fields are optional, but at least one is required.

        description (str, default = None): Product's new description
        sell_value (float, default = None): Product's new selling value. (can be 0, but not negative)
        barcode (str, default = None): Product's new barcode, must be unique
        section_id (int, default = None): ID of the product's new section/category
        stock (int, default = None): New initial stock of the product (can be 0, but not negative)
        expiration_date (str, default = None): Products new expiration date in format dd/mm/aaaa
        images (list:str, default = None) A list of the product's new images. Images must be a string in BASE64 encoded format. Headers are optional.
        
        Example request:
                {
                    "description": "A product name/description",
                    "sell_value": 10.50,
                    "barcode": "000000000000000000001",
                    "section_id": 5,
                    "stock": 10,
                    "expiration_date": "01/01/1964"
                    "images": ["UklGRkB7AABXRUJQVlA4IDR7AABw6AOdASqwB...", "UklGRuCRAABXRUJQVlA4INSRA..."]
                }

        Example return:
            {
                "message": "Produto atualizado com sucesso",
                "detail": {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                }
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem editar productes")
    try:
        product = Product(id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    
    values = []
    description_field = ''
    sell_value_field = ''
    barcode_field = ''
    section_id_field = ''
    stock_field = ''
    expiration_date_field = ''

    if new_information.description != None:
        if new_information.description == '':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Descrição inválida")
        description_field = 'description = %s, '
        values.append(new_information.description)
    
    if new_information.sell_value != None:
        if new_information.sell_value < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Preço de venda inválido")
        sell_value_field = 'sell_value = %s, '
        values.append(new_information.sell_value)
    
    if new_information.barcode != None:
        if new_information.barcode == '':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Barcode inválido")
        try:
            existing_product = Product(barcode=new_information.barcode)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Barcode já existe")
        except ObjectNotFound:
            barcode_field = 'barcode = %s, '
            values.append(new_information.barcode)
    
    if new_information.section_id != None:
        try:
            query = "SELECT * FROM sections WHERE id=%s"
            result = db_operations.select(query, (new_information.section_id,))
            if len(result) < 1:
                raise ObjectNotFound
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "ID de categoria inválido")
        section_id_field = 'section_id = %s, '
        values.append(new_information.section_id)
    
    if new_information.stock != None:
        if new_information.stock < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Estoque inválido")
        stock_field = 'stock = %s, '
        values.append(new_information.stock)

    if new_information.expiration_date != None:
        try:
            date_obj = datetime.strptime(new_information.expiration_date, "%d/%m/%Y")
            new_information.expiration_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Prazo de validade inválido")
        expiration_date_field = 'expiration_date = %s, '
        values.append(new_information.expiration_date)

    query = f"""UPDATE products SET
        {description_field}
        {sell_value_field}
        {barcode_field}
        {section_id_field}
        {stock_field}
        {expiration_date_field} WHERE id = %s """
    query = query.replace('\n', '')
    query = re.sub(' +', ' ', query)
    query = query.replace(", WHERE", " WHERE")
    values.append(id)
    result = db_operations.insert(query, values, "id")
    updated_product = Product(id = result)
    message = "Produto atualizado com sucesso"
    errored_image = False
    if new_information.images!=None:
        for image in new_information.images:
            try:
                updated_product.insert_image(image)
            except:
                if not errored_image:
                    message += ". Uma ou mais imagem não pôde ser salva..."
                    errored_image = True
    return {
        "message": message,
        "detail": updated_product.get_info()
    }

@app.delete("/products/{id}")
async def delete_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Deletes product from provided ID. Only admins can perform this action.
    
    If successful, returns success message.
    
    If product is not found, returns 204.

        id: ID of the product to be deleted

        Example return:
            {
                "message": "Produto deletado com sucesso"
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem deletar produtos")
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
        product = Product(id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    query = """
        DELETE FROM products WHERE id = %s
    """
    result = db_operations.insert(query, (id,))
    return {"message": "Produto deletado com sucesso"}

# ORDERS ROUTES ------------------------------------------------------------------------------------------------

@app.get("/orders")
async def get_orders(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    offset: Optional[int] = Query(0, ge=0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    id: Optional[int] = Query(0, ge=0),
    order_status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(0, ge=0)
):
    '''
    Returns order list, limit of 20 entries.
    All parameters are optional
    
        offset (int, default = 0): Sets the offset for the resulting list.
        start_date (str, format dd/mm/aaaa, default = None): Sets the start date to filter results. If unspecified, any result up to 1900-01-01 will be returned.
        end_date (str, format dd/mm/aaaa, default = None): Sets the start date to filter results. If unspecified, any result up to the newest will be returned.
        section (str, default = None): Filters containing the section. Must exist in sections database and be exact match (case insensitive).
        id (int, default = 0): Filters order by ID. Note that depending on other filters, it may not be returned. If the exact order is needed, it's recommended to use get(/orders/{id}).
        order_status (str, default = None): Filters by status. Must exist in orders_product database and be exact match (case insensitive).
        client_id (int, default = 0): Filters orders by client ID.

        Example parameters:
            offset: 10
            start_date: "31/01/2024"
            end_date: "31/10/2025"
            section: "Hortifruti"
            id: 10
            order_status: "Em transporte"
            client_id: 3

        Example return:
            [
                {
                    "id": 1,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Em separação",
                    "products": {
                        "1": {
                            "id": 12,
                            "description": "Refrigerante Cola 2L",
                            "sell_value": 8.99,
                            "barcode": "789100000012",
                            "section_name": "Bebidas",
                            "stock": 110,
                            "expiration_date": "2026-02-01",
                            "images": {
                                "0": "UklGRn..."
                            },
                            "quantity": 5
                        },
                        "2": {
                            "id": 7,
                            "description": "Manteiga com Sal",
                            "sell_value": 8.9,
                            "barcode": "789100000007",
                            "section_name": "Laticínios",
                            "stock": 60,
                            "expiration_date": "2025-12-15",
                            "images": {
                                "0": "UklGRs..."
                            },
                            "quantity": 28
                        }
                        [...]
                    }
                },
                {
                    "id": 2,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Nova",
                    "products": {...}
                }
            ]
                    
    '''
    args = []
    #date_field = "o.created_at AT TIME ZONE 'America/Sao_Paulo' BETWEEN %s AND %s "
    date_field = "o.created_at BETWEEN %s AND %s"
    section_field = ''
    id_field = ''
    order_status_field = ''
    client_id_field = ''
    if start_date != None:
        try:
            start_date = datetime.strptime(start_date, "%d/%m/%Y")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Data de início inválida")
    else:
        start_date = datetime.strptime('01/01/1900', "%d/%m/%Y")
    if end_date != None:
        try:
            end_date = datetime.strptime(end_date, "%d/%m/%Y")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Data de fim inválida")
    else:
        end_date = datetime.now(pytz.timezone('America/Sao_Paulo'))
    start_date = start_date.strftime("%Y-%m-%d") + " 00:00:00+00"
    end_date = end_date.strftime("%Y-%m-%d") + " 23:59:59+00"
    args.append(start_date)
    args.append(end_date)
    if section != None and section != '':
        try:
            section_id = utils.get_section_id(section)
            section_field = "AND s.id = '%s' "
            args.append(section_id)
        except utils.ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Categoria não localizada, por favor redefina o filtro")

    if id != None and id > 0:
        id_field = "AND o.id = '%s' "
        args.append(id)

    if order_status != None and order_status != '':
        try:
            order_status_id = utils.get_status_id(order_status)
            order_status_field = "AND o.status = '%s' "
            args.append(order_status_id)
        except utils.ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status não localizado, por favor redefina o filtro")

    if client_id != None and client_id > 0:
        try:
            client = Client(id = client_id)
            client_id_field = "AND c.id = '%s' "
            args.append(client_id)
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado, por favor redefina o filtro")
    args.append(offset)
    # query = f"""
    #     SELECT DISTINCT o.id
    #     FROM orders o
    #     JOIN orders_products op ON o.id = op.order_id
    #     JOIN products p ON op.product_id = p.id
    #     JOIN sections s ON p.section_id = s.id
    #     JOIN clients c ON o.client_id = c.id
    #     WHERE
    #     {date_field}
    #     {section_field}
    #     {id_field}
    #     {order_status_field}
    #     {client_id_field}
    #     LIMIT 20 OFFSET %s;
    # """
    query = f"""
        SELECT o.id
        FROM orders o
        JOIN orders_products op ON o.id = op.order_id
        JOIN products p ON op.product_id = p.id
        JOIN sections s ON p.section_id = s.id
        JOIN clients c ON o.client_id = c.id
        WHERE
        {date_field}
        {section_field}
        {id_field}
        {order_status_field}
        {client_id_field}
        GROUP BY o.id
        LIMIT 20 OFFSET %s;
    """
    query = re.sub('\n+', ' ', query)
    query = re.sub(' +', ' ', query)
    result_raw = db_operations.select(query, args)
    if len(result_raw) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    result = []
    for entry in result_raw:
        order = Order(entry)
        result.append(order.get_info())
    return result

@app.post("/orders")
async def create_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_order: NewOrder
):
    ''' Registers new order. Returns a success message and the ID of the new order.
    If user_id is not found, returns 400 with detail.
    
    If any item is not found, returns 400 with detail.
    
    If any quantity is bigger than product's stock, returns 400 with detail.
    
    All request values are required, at least one product is required.

        client_id(int): ID of the order's client (postive non-zero).
        products(list): A list of dictionaries containing two key-values pair: 'product_id'(int) and 'quantity'(int).
        
        Example request:
            {
                "client_id": 10,
                "products": [
                    {
                        "product_id": 2,
                        "quantity": 10
                    },
                    {
                        "product_id": 5,
                        "quantity": 3
                    }
                ]
            }

        Example return:
            {
                "message": "Ordem criada com sucesso",
                "id": order.id
            }

    '''
    if len(new_order.products)<1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ao menos um item obrigatório")
    try:
        client = Client(new_order.client_id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado")
    
    try:
        product_list = [
                {
                    'product':Product(x.product_id),
                    'quantity':x.quantity
                } for x in new_order.products
            ]
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produtos não localizado")
    
    insufficient_items = []
    for item in product_list:
        if item['quantity'] > item['product'].stock:
            insufficient_items.append(
                {
                    'product_id': item['product'].id,
                    'description': item['product'].description,
                    'stock': item['product'].stock,
                    'requested': item['quantity'],
                    'delta': item['product'].stock - item['quantity']
                }
            )
    if len(insufficient_items)>0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= {'message':"Um ou mais produtos não possui estoque sucifiente", 'details': insufficient_items})

    query = "INSERT INTO orders (client_id) VALUES (%s)"
    order = Order(db_operations.insert(query, (new_order.client_id,), 'id'))
    for item in product_list:
        order.include_product(item['product'].id, item['quantity'])
    
    return {"message": "Ordem criada com sucesso", "id": order.id}

@app.get("/orders/{id}")
async def get_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Returns an order by id
    id (int): Order's id to be returned

        Example Return:
            {
                "id": 5,
                "created_at": "2025-05-25T16:29:13.177126+00:00",
                "status": "Cancelada",
                "products": {
                    "1": {
                        "id": 6,
                        "description": "Café Torrado e Moído",
                        "sell_value": 14.5,
                        "barcode": "789100000006",
                        "section_name": "Marcearia",
                        "stock": 90,
                        "expiration_date": "2025-11-05",
                        "images": {
                            "0": "UklGRn..."
                        },
                        "quantity": 4
                    }, 
                    "2": {...},
                    [...]
                }
            }
    '''
    try:
        return Order(id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não localizada")
    
@app.put("/orders/{id}")
async def update_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_info: UpdateOrder
):
    ''' Updates order. Returns the order's detail if successfull.
        
    All request values are optional, but at least one is required.
    
    If new status is "Cancelado", products lists are ignored and all current products in order will be returned to stock.
    
    Orders with status "Cancelado" or "Entregue" cannot be modified.

        status (string, optional, default = None): Must be exact match from order_status table (case insensitive).
        products_to_include (list, optional, default = None): A list of dictionaries of products to be included in order containing two key-values pair:
            'product_id'(int) and 'quantity'(int).
        products_to_remove (list, optional, default = None): A list of dictionaries of products to be removed from order containing two key-values pair:
            'product_id'(int) and 'quantity'(int).

        Example request:
            {
                "id": 10,
                "products_to_include": [
                    {
                        "product_id": 2,
                        "quantity": 10
                    },
                    {
                        "product_id": 5,
                        "quantity": 3
                    }
                ]
            }

        Example return:
            {
                "message": "Ordem atualizada com sucesso",
                "details": {
                    "id": 6,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Em transporte",
                    "products": {
                        "1": {
                            "id": 1,
                            "description": "Leite Integral",
                            "sell_value": 4.5,
                            "barcode": "789100000001",
                            "section_name": "Laticínios",
                            "stock": 100,
                            "expiration_date": "2026-05-01",
                            "images": {
                                "0": "UklGRh..."
                            },
                            "quantity": 19
                        },
                        "2": {...},
                        [...]
                    }
                }
            }

    '''
    try:
        order = Order(id)
        if not order.is_open():
            raise OrderCantBeChanged
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status inválido")
    except OrderCantBeChanged:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não pode ser alterada. Verifique se a mesma não está cancelada ou entregue.")
    if new_info.status != None:
        try:
            status_id = utils.get_status_id(new_info.status)
        except utils.ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status inválido")
        try:
            if status_id == 1:
                order.cancel_order()
                return {"message": "Ordem cancelada com sucesso."}
        except OrderCantBeChanged:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não pode ser alterada. Verifique se a mesma não está cancelada ou entregue.")
    if new_info.products_to_include != None:
        try:
            for item in new_info.products_to_include:
                product = Product(item.product_id)
                quantity = item.quantity
                order.include_product(product.id, quantity)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto informado possui quantidade além do disponível no estoque.")
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não foi localizado")
    if new_info.products_to_remove != None:
        try:
            for item in new_info.products_to_remove:
                product = Product(item.product_id)
                quantity = item.quantity
                order.remove_product(product.id, quantity)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto informado possui quantidade além do disponível na ordem.")
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não foi localizado")
        except ItemNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não existe na ordem")
    order.change_status(status_id)
    return {
        "message": "Ordem atualizada com sucesso",
        "details": order.get_info()
    }

@app.delete("/orders/{id}")
async def delete_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Deletes order from provided ID. Only admins can perform this action.
    
    If successful, returns success message.
    
    If order is not found, returns 204.

        id: ID of the order to be deleted

        Example return:
            {
                "message": "Ordem deletada com sucesso"
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem deletar ordens")
    try:
        order = Order(id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    try:
        order.cancel_order()
    except:
        pass
    query = """
        DELETE FROM orders WHERE id = %s
    """
    result = db_operations.insert(query, (id,))
    return {"message": "Ordem deletada com sucesso"}