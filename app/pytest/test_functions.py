import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from datetime import datetime

from ..main import app
from ..utils import *
from ..db_classes import *

client = TestClient(app)

def test_get_password_hash_01():
    password = 'TesteDeSenha123'
    hashed_password = get_password_hash(password)
    assert hashed_password != password
    assert verify_password(password, hashed_password)

def test_get_password_hash_02():
    password = '123@srtA'
    hashed_password = get_password_hash(password)
    assert hashed_password != password
    assert verify_password(password, hashed_password)

def test_get_user_ok_01():
    user = get_user('test_admin')
    assert type(user) == db_classes.User

def test_get_user_fail_01():
    with pytest.raises(db_classes.ObjectNotFound):
        user = get_user('incorrect_user')
    
def test_authenticate_user_ok_db_01():
    user = authenticate_user('test_admin', 'test')
    assert type(user) == db_classes.User
    assert user.username == 'test_admin'
    assert user.password == '$2b$12$wc7m8.c8wa1eJrjEAdO3UODYqZkqhjeMln1bfpDuBKWCMb0GNcv8G'

def test_authenticate_user_ok_db_02():
    user = authenticate_user('test_op', 'test')
    assert type(user) == db_classes.User
    assert user.username == 'test_op'
    assert user.password == '$2b$12$wc7m8.c8wa1eJrjEAdO3UODYqZkqhjeMln1bfpDuBKWCMb0GNcv8G'

def test_authenticate_user_fail_db_01():
    with pytest.raises(db_classes.ObjectNotFound):
        user = authenticate_user('incorret', 'nonexistent')

def test_authenticate_user_fail_db_02():
    user = authenticate_user('test_admin', 'incorret_password')
    assert user == False

def test_authenticate_user_fail_db_03():
    user = authenticate_user('test_admin', '$2b$12$wc7m8.c8wa1eJrjEAdO3UODYqZkqhjeMln1bfpDuBKWCMb0GNcv8G')
    assert user == False

def test_validate_cpf_ok_01():
    assert validate_cpf('59375349055')
    assert validate_cpf('88005312024')
    assert validate_cpf('67979436040')

def test_validate_cpf_fail_01():
    assert not validate_cpf('12345')
    assert not validate_cpf(2)
    assert not validate_cpf('93872048191')

def test_generate_cpf_01():
    assert validate_cpf(generate_cpf())
    assert validate_cpf(generate_cpf())
    assert validate_cpf(generate_cpf())

def test_validade_email_ok_01():
    assert validate_email('abc@xyz.jkl')
    assert validate_email('asd@fdsf.us')
    assert validate_email('me@dot.jp')

def test_validade_email_fail_01():
    assert not validate_email('abcxyz.jkl')
    assert not validate_email('asd@fdsfus')
    assert not validate_email('me@dot.jp.com')
    assert not validate_email('@uai.com')