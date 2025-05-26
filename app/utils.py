from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

import db_classes
import db_operations

from base_models import TokenData, User
import random
import base64
import pytz

# Hash and secret declarations
SECRET_KEY = "4a69116ef9fb50ec1c0ee3499723ef5bc00cf504042e13605583f41e03191f2e"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error = False)

class ObjectNotFound(Exception):
    pass

def verify_password(plain_password:str, hashed_password:str) -> bool:
    ''' Verifies if a supplied password matches the hashed password and returns a bool indicating if matches.
    
    plain_password: supplied password.
    
    hashed_password: saved hashed password, typically stored in database.
    '''
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password:str) -> str:
    ''' Generates the hashed password for a given plain password. Useful for testing.
    
    password: Plain password to be hashed.
    '''
    return pwd_context.hash(password)


def get_user(username: str) -> db_classes.User:
    ''' Checks for existence of user in database and return as an instance of User from db_classes.
    Raises a ObjectNotFound error if does not exist.

    username: username to be searched in database.
    '''
    try:
        user = db_classes.User(username=username)
    except ObjectNotFound:
        raise ObjectNotFound
    if user:
        return user


def authenticate_user(username: str, password: str):
    ''' Authenticates the user against the stored password. If successful, returns the an instance of User from db_classes.
    If unsuccessful, returns a negative boolean. If user is not found, returns a ObjectNotFound exception.

    username: username to be searched in database.
    '''
    try:
        user = get_user(username)
    except ObjectNotFound:
        raise ObjectNotFound
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    ''' Creates a JWT access token as per FastAPI documentation. Returns the encoded JWT as string.
    
    data: dict containing key "sub" and the username, following jwt standard.

    expires_delta: the time for expiration. If not provided, 15 minutes will be used by default.
    '''
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> db_classes.User:
    ''' Checks if JWT token is valid for the current user. If valid, returns an instance of User from db_classes.
    If no username is stored in the token or is not found, or token is invalid, raises HTTPException and returns 401 status code.
    
    token: current token to be checked.
    '''
    # Creating the exception to return if not valid, following FastAPI documentation and standard
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    try:
        user = get_user(username=token_data.username)
    except ObjectNotFound:
        raise credentials_exception
    return user

def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> User:
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            return None
        existing_user = db_classes.User(username=username)
        return User(username = existing_user.username, role = existing_user.role, active = not existing_user.disabled)
    except InvalidTokenError:
        return None


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    ''' Checks if the current user is active.
    Returns an HTTPException with status code 400 if inactive.
    Returns the provided user if active.

    current_user: User to check if active.
    '''
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_client(query:str):
    '''Searchs for clients both from email or cpf (must be exact match).
    Returns an instance of Client from db_classes if found.
    Raises ObjectNotFound if no results.

    query: query to search, either cpf or email
    '''
    try:
        if validate_cpf(query):
            return db_classes.Client(cpf = query)
        if validate_email(query):
            return db_classes.Client(email = query)
        raise ObjectNotFound
    except ObjectNotFound:    
        raise ObjectNotFound
    
def validate_cpf(cpf:str) -> bool:
    ''' Validates if CPF is valid. Returns a bool.

    cpf: CPF to be validated
    '''
    if type(cpf) != str:
        return False
    
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False

    # First digit validation:
    numbers = [int(digit) for digit in cpf if digit.isdigit()]
    sum_of_products = sum(a*b for a, b in zip(numbers[0:9], range(10, 1, -1)))
    expected_digit = (sum_of_products * 10 % 11) % 10
    if numbers[9] != expected_digit:
        return False

    # Second digit validation:
    sum_of_products = sum(a*b for a, b in zip(numbers[0:10], range(11, 1, -1)))
    expected_digit = (sum_of_products * 10 % 11) % 10
    if numbers[10] != expected_digit:
        return False

    return True

def validate_email(email: str) -> bool:
    ''' Validates if email is valid. Returns a bool.

    For an email to be valid, must have x chars + '@' + y chars + '.' + z chars.

    email: email to be validated.
    '''
    try:
        address,server = email.split("@")
        if len(address) == 0:
            return False
        if server.count('.') != 1:
            return False
        
        provider, location = server.split(".")
        if len(provider) == 0:
            return False
        if len(location) == 0:
            return False
        
        return True
    except:
        return False
    
def generate_cpf():
    '''Generates random valid CPF
    '''
    cpf = [random.randint(0, 9) for x in range(9)]                              
    for i in range(2):
        val = sum([(len(cpf) + 1 - j) * v for j, v in enumerate(cpf)]) % 11
        cpf.append(11 - val if val > 1 else 0)
    string_cpf = [str(x) for x in cpf]
    return ''.join(string_cpf)

def get_section_id(db_cursor, name: str):
    try:
        name = '%'+name.lower()+'%'
        section_id = db_operations.select(db_cursor, "SELECT id from sections where name ILIKE %s LIMIT 1", (name,), 1)[0]
        return section_id
    except:
        raise ObjectNotFound

def get_status_id(db_cursor, name: str):
    try:
        name = '%'+name.lower()+'%'
        status_id = db_operations.select(db_cursor, "SELECT id from order_status where description ILIKE %s LIMIT 1", (name,), 1)[0]
        return status_id
    except:
        raise ObjectNotFound

def convert_to_local_timezone(time: datetime, local_timezone:str = 'America/Sao_Paulo'):
    local_tz = pytz.timezone(local_timezone)
    dt_local = time.astimezone(local_tz)
    return dt_local.strftime('%d/%m/%Y %H:%M:%S')
