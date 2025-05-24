from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import re

from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

import db_operations
import utils
from base_models import Token, User, NewUser, NewClient, UpdateClient, NewProduct, UpdateProduct
from db_classes import ObjectNotFound, Client, Product

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

        Example request:
            {
                "username": "a_new_username",
                "password": "a_new_password",
                "role": 1 # optional, defaults to lowest role
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
    
        offset: (optional, default = 0) Sets the offset for the resulting list.
        filter: (optional, default = None) Filter results by name and email using the specified keyword.
    '''
    additional_sting = ''
    if filter != None and filter != '':
        filter = '%'+filter.lower()+'%'
        additional_sting = "WHERE name ILIKE %s OR email ILIKE %s"
        args = (filter, filter, offset,)
    else:
        args = (offset,)
    query = f"""SELECT * FROM clients {additional_sting} LIMIT 20 OFFSET %s"""
    result_raw = db_operations.select(query, args)
    if len(result_raw) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    result = []
    for entry in result_raw:
        result.append({
            "id": entry[0],
            "name": entry[1],
            "email": entry[2],
            "cpf": entry[3],
        })
    return result

@app.post("/clients")
async def create_client(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_client: NewClient
):
    """ Registers new client.  Returns a success message and the ID of the new user.
    
    All three fields are required. Email and CPF must be valid and unique.

        name: Client's name.
        email: Client's email (must be valid and unique).
        cpf: Client's cpf (must be valid and unique).

        Example request:
                {
                    "name": "a_valid_name",
                    "email": "a_valid_and_unique_email",
                    "cpf": "a_valid_and_unique_cpf"
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

    Returns 204 if no client is found.

        id: ID of the client to searched
    '''
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
        client = Client(id = id)
        return {
            "id": client.id,
            "nome": client.name,
            "email": client.email,
            "cpf": client.cpf
        }
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    
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

        id: ID of the client to be updated
        name: Client's new name.
        email: Client's new email (must be valid and unique).
        cpf: Client's new cpf (must be valid and unique).

        Example requests:
                {
                    "name": "a_valid_new_name",
                    "email": "a_valid_and_unique_new_email",
                    "cpf": "a_valid_and_unique_new_cpf"
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
        "id": updated_client.id,
        "nome": updated_client.name,
        "email": updated_client.email,
        "cpf": updated_client.cpf
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
    price: Optional[float] = Query(0, ge=0),
    available: Optional[bool] = Query(False)
):
    '''Returns products list, limit of 20 entries.
    
        offset:int (optional, default = 0) Sets the offset for the resulting list.
        category:str (optional, default = None) Filter results by section.
        price:float (optional, default = 0) Filter results lower than the specified price if > 0.
        available:bool (optional, default = False) Filter only results with items in stock if True
    '''
    additional_sting = ''
    args = []
    category_string = ''
    price_string = ''
    available_string = ''
    if category != None and category != '':
        try:
            category_id = utils.get_section_id(category)
            category_string = "section_id = %s AND "
            args.append(category_id)
        except ObjectNotFound:
            raise HTTPException(status_code=400, detail= "Categoria não localizada, por favor redefina o filtro")
    
    if price > 0:
        price_string = "sell_value <= %s AND "
        args.append(price)

    if available:
        available_string = "stock > 0 AND "
    
    args.append(offset)
    query = f"""
        SELECT * FROM products {category_string}{price_string}{available_string} LIMIT 20 OFFSET %s
    """
    query = re.sub(' +', ' ', query)
    query = query.replace(" AND LIMIT", " LIMIT")
    if len(category_string+price_string+available_string)>0:
        query = query.replace("FROM products", "FROM products WHERE")
    print(query)
    print(args)
    result_raw = db_operations.select(query, args)
    if len(result_raw) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    result = []
    for entry in result_raw:
        try: 
            images = utils.get_product_images_from_id(entry[0])
        except ObjectNotFound:
            images = {}
            
        result.append({
            "id": entry[0],
            "description": entry[1],
            "price": entry[2],
            "barcode": entry[3],
            "section_id": entry[4],
            "stock": entry[5],
            "expiration_date": entry[6],
            "images": images
        })
    return result

#POST /products: Criar um novo produto, contendo os seguintes atributos: descrição, valor de venda, código de barras, seção, estoque inicial, e data de validade (quando aplicável) e imagens.

@app.post("/products")
async def create_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_product: NewProduct
):
    """ Registers new product. Returns a success message and the ID of the new user.

    Only admins can create products.

    All fields are required, except for expiration_date.

        description(str): Product's description        
        sell_value(float): Product's selling value        
        barcode(str): Product's barcode, must be unique        
        section_id(int): ID of the product's section/category        
        stock(int): Initial stock of the product (must be greater than 0)        
        expiration_date(str) (Optional): Products expiration date in format dd/mm/aaaa        
        images(list:str) (Optional) A list of the product images. Images must be a string in BASE64 encoded format. Headers are optional

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
        print(existing_product)
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
        message = "Produto cadastrado com sucesso"
        saved_images = []
        errored_image = False
        if new_product.images!=None:
            for image in new_product.images:
                try:
                    saved_images.append(utils.save_image_to_bytea_sql(image, result))
                except:
                    if not errored_image:
                        message += ". Uma ou mais imagem não pôde ser salva..."
                        errored_image = True
        return {
            "message": message,
            "id": result,
            "saved_images_id": saved_images
            }

@app.get("/products/{id}")
async def get_produc_by_id(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    ''' Returns a product properties identified by id.

    Returns 204 if no product is found.

        id: ID of the product to be searched
    '''
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
        product = Product(id = id)
        return {
            'id': product.id,
            'description': product.description,
            'sell_value': product.sell_value,
            'barcode': product.barcode,
            'section_id': product.section_id,
            'stock': product.stock,
            'expiration_date': product.expiration_date,
            'images': utils.get_product_images_from_id(product.id)
        }
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    
@app.put("/products/{id}")
async def put_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_information: UpdateProduct
):
    ''' Updates a product by id. Only admins can update products.
    
    If successful, returns the updated properties of the product.
    
    Returns 204 if no product is found.
    
    Accepts any property of products to update, except ID which cannot be changed. At least one is required.

        description(str): Product's new description        
        sell_value(float): Product's new selling value. (can be 0, but not negative)        
        barcode(str): Product's new barcode, must be unique        
        section_id(int): ID of the product's new section/category        
        stock(int): New initial stock of the product (can be 0, but not negative)        
        expiration_date(str) (Optional): Products new expiration date in format dd/mm/aaaa        
        images(list:str) (Optional) A list of the product's new images. Images must be a string in BASE64 encoded format. Headers are optional
        
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
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem editar productes")
    try:
        if type(id) != int or id<1:
            raise ObjectNotFound
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
    print('\n\n\n\n\n\n\n')
    print(query)
    print('\n\n\n\n\n\n\n')
    values.append(id)
    result = db_operations.insert(query, values, "id")
    updated_product = Product(id = result)
    message = "Produto atualizado com sucesso"
    errored_image = False
    if new_information.images!=None:
        for image in new_information.images:
            try:
                utils.save_image_to_bytea_sql(image, result)
            except:
                if not errored_image:
                    message += ". Uma ou mais imagem não pôde ser salva..."
                    errored_image = True
    return {
        "message": message,
        'id': updated_product.id,
        'description': updated_product.description,
        'sell_value': updated_product.sell_value,
        'barcode': updated_product.barcode,
        'section_id': updated_product.section_id,
        'stock': updated_product.stock,
        'expiration_date': updated_product.expiration_date,
        'images': utils.get_product_images_from_id(updated_product.id)
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
