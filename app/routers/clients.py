from fastapi import APIRouter
from typing import Annotated, Optional
import re

from fastapi import Depends, HTTPException, status, Query

import db_operations
import utils

from base_models import User, NewClient, UpdateClient
from db_classes import ObjectNotFound, Client, admin_role_id

router = APIRouter()

# CLIENTS ROUTES ------------------------------------------------------------------------------------------------


@router.get("/clients")
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
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        result_raw = db_operations.select(db_cursor, query, args)
        if len(result_raw) == 0:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        result = []
        for entry in result_raw:
            client = Client(db_cursor, entry[0])
            result.append(client.get_info())
        return result
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.post("/clients")
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
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        result = db_operations.insert(db_cursor, query, args, 'id')
        db_connection.commit()
        db_cursor.close()
        db_connection.close()
        return {"message": "Cliente cadastrado com sucesso", "id": result}

@router.get("/clients/{id}")
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
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        return Client(db_cursor, id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado")
    finally:
        db_cursor.close()
        db_connection.close()

@router.put("/clients/{id}")
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
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            if type(id) != int or id<1:
                raise ObjectNotFound
            client = Client(db_cursor, id = id)
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
        result = db_operations.insert(db_cursor, query, values, "id")
        updated_client = Client(db_cursor, id = result)
        if updated_client.get_info() == client.get_info():
            raise
        db_connection.commit()
        return {
            "message": "Cliente atualizado com sucesso",
            "detail": updated_client.get_info()
        }
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.delete("/clients/{id}")
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
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            if type(id) != int or id<1:
                raise ObjectNotFound
            client = Client(db_cursor, id = id)
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        query = """
            DELETE FROM clients WHERE id = %s
        """
        result = db_operations.insert(db_cursor, query, (id,))
        db_connection.commit()
        return {"message": "Cliente deletado com sucesso"}
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()
