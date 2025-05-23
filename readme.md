# Teste Técnico - Infog2

Repositório criado para o teste técnico

# Como utilizar (Com Docker)

<p> Clone o repositório, monte o docker-compose e aguarde os containers iniciarem</p>

```powershell
docker-compose up
```

Após a inicialização dos serviços, o servidor poderá ser acessado através do endereço <i><b>localhost:5000</b></i>.
O log do container app deve ser parecido com este:

```powershell
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:80⁠ (Press CTRL+C to quit)
```

# Como utilizar (Sem Docker)

Para utilização sem docker, são necessários passos adicionais, e certos caminhos ou configurações podem ser diferentes de uma máquina para outra

## Antes de começar
Esta aplicação utiliza o Python 3.13.3.

Caso ainda não possua, os seguintes pacotes também são necessários:

``` powershell
pip install psycopg2
pip install "fastapi[standard]"
pip install python-multipart
pip install "python-jose[cryptography]"
pip install "passlib[bcrypt]"
pip install --no-cache-dir fastapi uvicorn
pip install jwt
pip install pyjwt
```

O banco de dados utilizados é o PostgreSQL versão 17.5.
Note que a aplicação se conecta com o banco utilizando a porta 5431.
Caso necessite inicializar o banco, o arquivo de inicialização está em /postgresql/init.sql

Caso utilize uma outra imagem de container, copie o arquivo para o caminho /docker-entrypoint-initdb.d/ e expose a porta correta.

## Utilizando
Após clonar o repositório, navegue até a pasta /app.

Execute o comando a seguir:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

# Acessando o banco

O banco criado na imagem Docker possui a seguinte autenticação e database nas variáveis de ambiente:

```powershell
POSTGRES_USER = admin
POSTGRES_PASSWORD = admin
POSTGRES_DB =  infog2
```

# Testes

Em <i>/app/pytest/</i> se encontram os arquivos de testes.
Para os que necessitam de autenticação, temos dois usuários previamente criados, e também seus tokens para teste (expiram em 2026/05/23):
```python
username: 'test_admin'
password: 'test'
token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2FkbWluIiwiZXhwIjozNTc5NTU3MjI0fQ.TUlWVlBMlXsZHq3KOob3k9W4yxWSyntLpLt5NBLU5nk'

username: 'test_op'
password: 'test'
token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X29wIiwiZXhwIjozNTc5NTU3MjYwfQ.4MBK3vdUqg1E1r_ITkNv7gnbSdktO-43lAo57dhR3J0'
```

Estes usuários também podem ser utilizados para teste via Postman ou pela documentação interativa do FastAPI

Caso necessite atualizar os tokens, eles se encontram em <i>/app/pytest/tokens.py</i>.

Para executar os testes, retorne para a pasta <i>/app</i> e execute o comando:
```powershell
pytest
```
ou
```powershell
python -m pytest
```