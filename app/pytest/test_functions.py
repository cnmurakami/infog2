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