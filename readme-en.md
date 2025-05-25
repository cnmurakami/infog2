[![Language](https://img.shields.io/badge/lang-pt--BR-green.svg)](https://github.com/cnmurakami/infog2/blob/main/readme.md)
[![Language](https://img.shields.io/badge/lang-en--US-blue.svg)](https://github.com/cnmurakami/infog2/blob/main/readme-en.md)

# Test - Infog2

Repository created for the technical test.

# How to use (With Docker)

Clone the repository, build the docker-compose, and wait for the containers to start.

```powershell
docker-compose up -d
```

After the services are up, the server can be accessed at <i><b>localhost:5000</b></i> (configured in docker-compose).

The container app logs should look like this:

```powershell
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:80 (Press CTRL+C to quit)
```

# How to use (Without Docker)

To run without Docker, some additional steps are required, and certain paths or configurations may vary depending on your machine.

# Before you start
This application uses Python 3.13.3.

If you don’t have it yet, the following packages are also required:

```powershell
pip install psycopg2
pip install "fastapi[standard]"
pip install python-multipart
pip install "python-jose[cryptography]"
pip install "passlib[bcrypt]"
pip install --no-cache-dir fastapi uvicorn
pip install pytz
pip install jwt
pip install pyjwt
pip install pytest
```

The database used is PostgreSQL version 17.5.
Note that the application connects to the database using port 5431.
If you need to initialize the database, the initialization script is located at /postgresql/init.sql.

If you are using a different container image, copy the file to /docker-entrypoint-initdb.d/ and expose the correct port.

## Running
After cloning the repository, navigate to the /app folder.

Run the following command:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

In this case, the application will be running at <i><b>localhost:8000</b></i>.

Due to environment differences, the application will attempt to connect to the database in two ways: via localhost on port 5431 or via db on port 5432 (when using Docker).
Adjust the database settings accordingly.

# Accessing the Database

The database created in the Docker image uses the following credentials (from environment variables):

```powershell
POSTGRES_USER = admin
POSTGRES_PASSWORD = admin
POSTGRES_DB = infog2
```

# Tests

## Using Docker
Access the app container’s terminal and run pytest. The container name is expected to be teste-infog2-app-1, but if it differs, use docker ps to list containers.

```powershell
docker ps

docker exec -it teste-infog2-app-1 sh 

pytest
```

By default, the container terminal should be in the correct folder. If not, change to it with:

```powershell
cd /app

pytest
```

## Running Locally

In /app/pytest/ you’ll find the test files.
For the tests that require authentication, there are two pre-created users along with their tokens for testing (tokens expire on 2026/05/23):

```python
username: 'test_admin'
password: 'test'
token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2FkbWluIiwiZXhwIjozNTc5NTU3MjI0fQ.TUlWVlBMlXsZHq3KOob3k9W4yxWSyntLpLt5NBLU5nk'

username: 'test_op'
password: 'test'
token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X29wIiwiZXhwIjozNTc5NTU3MjYwfQ.4MBK3vdUqg1E1r_ITkNv7gnbSdktO-43lAo57dhR3J0'
```

These users can also be used for testing via Postman or through the interactive FastAPI documentation.

If you need to update the tokens, they are located in <i>/app/pytest/tokens.py</i>.

To run the tests, go back to the </i>/app</i> folder and run:

```powershell
pytest
```