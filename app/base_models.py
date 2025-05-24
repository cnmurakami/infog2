from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    role: int | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str

class NewUser(BaseModel):
    username: str
    password: str
    role: int | None = None

class NewClient(BaseModel):
    name: str
    email: str
    cpf: str

class UpdateClient(BaseModel):
    name: str | None = None
    email: str | None = None
    cpf: str | None = None

class NewProduct(BaseModel):
    description: str
    sell_value: float
    barcode: str
    section_id: int
    stock: int
    expiration_date: str | None = None
    images: list | None = None

class UpdateProduct(BaseModel):
    description: str | None = None
    sell_value: float | None = None
    barcode: str | None = None
    section_id: int | None = None
    stock: int | None = None
    expiration_date: str | None = None
    images: list | None = None
