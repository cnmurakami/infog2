import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from datetime import datetime

from ..main import app
from ..utils import *
from ..db_classes import *
from .tokens import admin, operator

client = TestClient(app)

def test_get_orders_01():
    response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},)
    assert response.status_code == 200
    assert len(response.json()) == 20

def test_get_orders_02():
    first_response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},)
    second_response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'offset':5
        })
    assert second_response.status_code == 200
    assert second_response.json()[0] == first_response.json()[5]

def test_get_orders_03():
    response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'section':'Higiene'
        })
    assert response.status_code == 200
    assert all(
        any(product["section_name"] == 'Higiene' for product in order["products"].values())
        for order in response.json()
    )

def test_get_orders_04():
    response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'section':'Limpeza'
        })
    assert response.status_code == 200
    assert all(
        any(product["section_name"] == 'Limpeza' for product in order["products"].values())
        for order in response.json()
    )

def test_get_orders_05():
    response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'order_status':'Em transporte'
        })
    assert response.status_code == 200
    assert all(order["status"] == 'Em transporte' for order in response.json())

def test_get_orders_06():
    response = client.get(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        params={
            'client_id': 3
        })
    assert response.status_code == 200
    assert all(order["client_id"] == 3 for order in response.json())

def test_create_orders_ok_01():
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {operator}"},
        json={
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
        })
    assert response.status_code == 200
    assert response.json()["message"] == "Ordem criada com sucesso"

def test_create_orders_fail_01():
    response = client.post(
        "/orders",
        json={
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
        })
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_create_orders_fail_02():
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "client_id": 10,
            "products": [
                {
                    "product_id": 2,
                    "quantity": 10000
                },
                {
                    "product_id": 5,
                    "quantity": 100000
                }
            ]
        })
    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Um ou mais produtos não possui estoque sucifiente"

def test_create_orders_fail_03():
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "client_id": -1,
            "products": [
                {
                    "product_id": 2,
                    "quantity": 10000
                },
                {
                    "product_id": 5,
                    "quantity": 100000
                }
            ]
        })
    assert response.status_code == 400
    assert response.json()["detail"] == "Cliente não localizado"

def test_create_orders_fail_04():
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "client_id": 2,
            "products": [
            ]
        })
    assert response.status_code == 400
    assert response.json()["detail"] == "Ao menos um item obrigatório"

def test_get_order_ok_01():
    response = client.get(
        "/orders/8",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 200
    assert response.json()['id'] == 8
    assert response.json()['client_id'] == 14

def test_get_order_ok_02():
    response = client.get(
        "/orders/2",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 200
    assert response.json()['id'] == 2
    assert response.json()['client_id'] == 12

def test_get_order_fail_01():
    response = client.get(
        "/orders/-1",
        headers={"Authorization": f"Bearer {operator}"},
        )
    assert response.status_code == 400

def test_get_order_fail_02():
    response = client.get(
        "/orders/1"
        )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }

def test_delete_order_ok_01():
    product_1 = Product(2)
    product_2 = Product(5)
    initial_stock_product_1 = product_1.stock
    initial_stock_product_2 = product_2.stock
    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {admin}"},
        json={
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
        })
    assert create_response.status_code == 200
    assert create_response.json()['message'] == 'Ordem criada com sucesso'
    product_1 = Product(2)
    product_2 = Product(5)
    updated_stock_product_1 = product_1.stock
    updated_stock_product_2 = product_2.stock
    assert updated_stock_product_1 == initial_stock_product_1 - 10
    assert updated_stock_product_2 == initial_stock_product_2 - 3
    id = create_response.json()['id']

    delete_response = client.delete(
        f"/orders/{id}",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()['message'] == 'Ordem deletada com sucesso'
    with pytest.raises(ObjectNotFound):
        Order(id).get_images() == {}
    product_1 = Product(2)
    product_2 = Product(5)
    final_stock_product_1 = product_1.stock
    final_stock_product_2 = product_2.stock
    assert final_stock_product_1 == initial_stock_product_1
    assert final_stock_product_2 == initial_stock_product_2

def test_delete_order_fail_01():
    response = client.delete(
        "/orders/1",
        headers={"Authorization": f"Bearer {operator}"},
    )
    assert response.status_code == 403
    assert response.json()['detail'] == 'Apenas Admins podem deletar ordens'

def test_delete_order_fail_02():
    response = client.delete(
        "/orders/-1",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert response.status_code == 204