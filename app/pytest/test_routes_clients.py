import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from datetime import datetime

from ..main import app
from ..utils import *
from ..db_classes import *
from .tokens import admin, operator

client = TestClient(app)

def test_get_clients_01():
    response = client.get(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},)
    assert response.status_code == 200
    assert len(response.json()) == 20

def test_get_clients_02():
    first_response = client.get(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},)
    second_response = client.get(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'offset':5
        })
    assert second_response.status_code == 200
    assert second_response.json()[0] == first_response.json()[5]

def test_get_clients_03():
    response = client.get(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'filter': 'cameron'
        })
    assert response.status_code == 200
    assert response.json()[0] == {
        "id": 14,
        "name": "Vicente Cameron",
        "email": "vicente.cameron@gmail.com",
        "cpf": "11860140084"
    }

def test_get_clients_04():
    response = client.get(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'filter': 'aaaaaa'
        })
    assert response.status_code == 204

def test_create_client_ok_01():
    name = f'test{datetime.now()}'
    email = f'test{datetime.now()}@test.com'
    cpf = generate_cpf()
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 200
    assert response.json()['message'] == 'Cliente cadastrado com sucesso'

def test_create_client_fail_01():
    name = f'test{datetime.now()}'
    email = f'test{datetime.now()}@test.com'
    cpf = generate_cpf()
    response = client.post(
        "/clients",
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }

def test_create_client_fail_02():
    name = ''
    email = f'test{datetime.now()}@test.com'
    cpf = generate_cpf()
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Nome não pode ser vazio"
    }
    
def test_create_client_fail_03():
    name = f'test{datetime.now()}'
    email = f'test{datetime.now()}@test.com'
    cpf = '1234'
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 400
    assert response.json() == {
        "detail": "CPF inválido"
    }

def test_create_client_fail_04():
    name = f'test{datetime.now()}'
    email = 'aaa'
    cpf = generate_cpf()
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 400
    assert response.json() == {
        "detail": "E-mail inválido"
    }

def test_create_client_fail_05():
    name = f'test{datetime.now()}'
    email = f'test{datetime.now()}@test.com'
    cpf = '37030645014'
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 400
    assert response.json() == {
        "detail": "CPF já existe"
    }

def test_create_client_fail_06():
    name = f'test{datetime.now()}'
    email = 'nadine.curtis@gmail.com'
    cpf = generate_cpf()
    response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Email já existe"
    }

def test_get_client_ok_01():
    response = client.get(
        "/clients/1",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 200
    assert response.json()['nome'] == 'Laurence Howe'

def test_get_client_ok_02():
    response = client.get(
        "/clients/10",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 200
    assert response.json()['nome'] == 'Angela Watts'

def test_get_client_fail_01():
    response = client.get(
        "/clients/-1",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 204

def test_get_client_fail_02():
    response = client.get(
        "/clients/aaa",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 422

def test_get_client_fail_03():
    response = client.get(
        "/clients/1",
        )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }

def test_update_client_ok_01():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "name": "Fulano",
            "email": "abcd@aha.com"
        })
    assert response.status_code == 200
    assert response.json()["message"] == 'Cliente atualizado com sucesso'
    assert response.json()["nome"] == 'Fulano'
    assert response.json()["email"] == 'abcd@aha.com'

def test_update_client_ok_02():
    new_cpf = generate_cpf()
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "cpf": new_cpf
        })
    assert response.status_code == 200
    assert response.json()["message"] == 'Cliente atualizado com sucesso'
    assert response.json()["cpf"] == new_cpf

def test_update_client_ok_03():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "name": "Nadine Curtis",
            "email": "nadine.curtis@gmail.com",
            "cpf": '37030645014'
        })
    assert response.status_code == 200
    assert response.json()["message"] == 'Cliente atualizado com sucesso'
    assert response.json()["nome"] == 'Nadine Curtis'
    assert response.json()["email"] == 'nadine.curtis@gmail.com'
    assert response.json()["cpf"] == '37030645014'

def test_update_client_fail_01():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {operator}"},
        json = {
            "name": "Nathan",
            "email": "mynewemail@gmail.com",
            "cpf": generate_cpf()
        })
    assert response.status_code == 403
    assert response.json()["detail"] == 'Apenas Admins podem editar clientes'

def test_update_client_fail_02():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "name": "",
        })
    assert response.status_code == 400
    assert response.json()["detail"] == 'Nome inválido'

def test_update_client_fail_03():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "cpf": '123',
        })
    assert response.status_code == 400
    assert response.json()["detail"] == 'CPF inválido'

def test_update_client_fail_04():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "cpf": '59375349055',
        })
    assert response.status_code == 400
    assert response.json()["detail"] == 'CPF já existe'

def test_update_client_fail_05():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "email": 'laurence.howe',
        })
    assert response.status_code == 400
    assert response.json()["detail"] == 'E-mail inválido'

def test_update_client_fail_05():
    response = client.put(
        "clients/5",
        headers={"Authorization": f"Bearer {admin}"},
        json = {
            "email": 'laurence.howe@gmail.com',
        })
    assert response.status_code == 400
    assert response.json()["detail"] == 'E-mail já existe'

def test_delete_client_ok_01():
    name = f'test{datetime.now()}'
    email = f'test{datetime.now()}@test.com'
    cpf = generate_cpf()
    create_response = client.post(
        "/clients",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            'name': name,
            'email': email,
            'cpf': cpf
        })
    assert create_response.status_code == 200
    assert create_response.json()['message'] == 'Cliente cadastrado com sucesso'
    id = create_response.json()['id']
    delete_response = client.delete(
        f"/clients/{id}",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()['message'] == 'Cliente deletado com sucesso'

def test_delete_client_fail_01():
    response = client.delete(
        "/clients/1",
        headers={"Authorization": f"Bearer {operator}"},
    )
    assert response.status_code == 403
    assert response.json()['detail'] == 'Apenas Admins podem deletar clientes'

def test_delete_client_fail_02():
    response = client.delete(
        "/clients/-1",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert response.status_code == 204