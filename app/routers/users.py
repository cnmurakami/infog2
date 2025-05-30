from fastapi import APIRouter
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm

import db_operations
import utils

from base_models import Token, User, NewUser
from db_classes import ObjectNotFound, admin_role_id

router = APIRouter()

# USER ROUTES ------------------------------------------------------------------------------------------------

@router.post("/auth/register")
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
        try:
            db_connection = db_operations.postgres_connection();
            db_cursor = db_connection.cursor()
            query = """SELECT id from roles ORDER BY id DESC LIMIT 1"""
            lowest_role_id = db_operations.select(db_cursor, query=query, fetch=1)[0]
            if form_data.role:
                if not current_user:
                    raise HTTPException(status_code=403, detail= "Precisa estar logado para definir permissão")
                if form_data.role < 1 or form_data.role > lowest_role_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Permissão fornecida não existe")
                if form_data.role < current_user.role:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Sem autorização para criar usuário com as permissões fornecidas")
                query = """INSERT INTO users (username, password_hash, role_id) VALUES(%s, %s, %s)"""
                result = db_operations.insert(db_cursor, query, (form_data.username, encrypted_password, form_data.role, ), "id")
            else:
                query = """INSERT INTO users (username, password_hash) VALUES(%s, %s)"""
                result = db_operations.insert(db_cursor, query, (form_data.username, encrypted_password,), "id")
            db_connection.commit()
            return {"message": "Usuário cadastrado com sucesso", "id": result}
        except:
            raise
        finally:
            db_cursor.close()
            db_connection.close()



@router.post("/token")
@router.post("/auth/login")
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
    db_connection = db_operations.postgres_connection();
    db_cursor = db_connection.cursor()
    db_operations.insert(db_cursor, "INSERT INTO tokens (user_id, token, expire_at) VALUES (%s, %s, %s);",
                         (user.id, access_token, sql_timestamp_string,))
    db_connection.commit()
    db_cursor.close()
    db_connection.close()
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/refresh-token")
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
    db_connection = db_operations.postgres_connection();
    db_cursor = db_connection.cursor()
    db_operations.insert(db_cursor, "INSERT INTO tokens (user_id, token, expire_at) VALUES (%s, %s, %s);",
                         (current_user.id, access_token, sql_timestamp_string,))
    db_connection.commit()
    db_cursor.close()
    db_connection.close()
    return Token(access_token=access_token, token_type="bearer")

