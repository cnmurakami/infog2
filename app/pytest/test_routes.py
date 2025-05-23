import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from datetime import datetime

from ..main import app
from ..utils import *
from ..db_classes import *
from .tokens import admin, operator

client = TestClient(app)

def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Lu Estilo"}

def test_post_register_standard_ok_01():
    username = f'test{datetime.now()}'
    response = client.post(
        "/auth/register",
        json={
            'username': username,
            'password': '1234'
        })
    assert response.status_code  == 200

def test_post_register_standard_fail_01():
    response = client.post(
        "/auth/register",
        json={
            'username': 'test_admin',
            'password': '1234'
        })
    assert response.status_code  == 400
    assert response.json() == { "detail": "Usuário já existe" }

def test_post_register_standard_fail_02():
    response = client.post(
        "/auth/register",
        json={
            'username': '',
            'password': '1234'
        })
    assert response.status_code  == 400
    assert response.json() == { "detail": "Usuário e/ou senha em branco" }
    
def test_post_register_standard_fail_03():
    response = client.post(
        "/auth/register",
        json={
            'username': 'novo_usuario',
            'password': ''
        })
    assert response.status_code  == 400
    assert response.json() == { "detail": "Usuário e/ou senha em branco" }
    
def test_post_register_with_role_fail_01():
    username = f'test{datetime.now()}'
    response = client.post(
        "/auth/register",
        json={
            'username': username,
            'password': '1234',
            'role': '1'
        })
    assert response.status_code  == 403
    assert response.json() == {
        "detail": "Precisa estar logado para definir permissão"
    }

def test_post_register_with_role_fail_02():
    username = f'test{datetime.now()}'
    response = client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'username': username,
            'password': '1234',
            'role': '1'
        })
    assert response.status_code  == 403
    assert response.json() == {
        "detail": "Sem autorização para criar usuário com as permissões fornecidas"
    }

def test_post_register_with_role_ok_02():
    username = f'test{datetime.now()}'
    response = client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {operator}"},
        json={
            'username': username,
            'password': '1234',
            'role': '2'
        })
    assert response.status_code  == 200

def test_post_register_with_role_ok_03():
    username = f'test{datetime.now()}'
    response = client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            'username': username,
            'password': '1234',
            'role': '1'
        })
    assert response.status_code  == 200
