from fastapi import FastAPI
from routers import clients, orders, products, users

app = FastAPI()

app.include_router(users.router)
app.include_router(clients.router)
app.include_router(products.router)
app.include_router(orders.router)

@app.get("/")
def index():
    return {"message":"Lu Estilo"}

