from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import re

from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

import db_operations
import utils
from base_models import Token, User, NewUser, NewClient, UpdateClient
from db_classes import ObjectNotFound, Client

app = FastAPI()

@app.get("/")
def index():
    return {"message":"Lu Estilo"}

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


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(utils.get_current_active_user)]
):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]

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
    
    email: Client's email.

    cpf: Client's cpf.
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
    
    id = ID to be searched in database.
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
    
    id = ID to be searched in database.
    '''
    if current_user.role > 1:
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
    args:tuple = (x for x in values)
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
    if current_user.role > 1:
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