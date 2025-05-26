from fastapi import APIRouter
from datetime import datetime
from typing import Annotated, Optional
import re
import pytz

from fastapi import Depends, HTTPException, status, Query

import db_operations
import utils

from base_models import User, NewOrder, UpdateOrder
from db_classes import ObjectNotFound, ItemNotFound, OrderCantBeChanged, Client, Product, Order, admin_role_id

router = APIRouter()

# ORDERS ROUTES ------------------------------------------------------------------------------------------------

@router.get("/orders")
async def get_orders(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    offset: Optional[int] = Query(0, ge=0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    id: Optional[int] = Query(0, ge=0),
    order_status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(0, ge=0)
):
    '''
    Returns order list, limit of 20 entries.
    All parameters are optional
    
        offset (int, default = 0): Sets the offset for the resulting list.
        start_date (str, format dd/mm/aaaa, default = None): Sets the start date to filter results. If unspecified, any result up to 1900-01-01 will be returned.
        end_date (str, format dd/mm/aaaa, default = None): Sets the start date to filter results. If unspecified, any result up to the newest will be returned.
        section (str, default = None): Filters containing the section. Must exist in sections database and be exact match (case insensitive).
        id (int, default = 0): Filters order by ID. Note that depending on other filters, it may not be returned. If the exact order is needed, it's recommended to use get(/orders/{id}).
        order_status (str, default = None): Filters by status. Must exist in orders_product database and be exact match (case insensitive).
        client_id (int, default = 0): Filters orders by client ID.

        Example parameters:
            offset: 10
            start_date: "31/01/2024"
            end_date: "31/10/2025"
            section: "Hortifruti"
            id: 10
            order_status: "Em transporte"
            client_id: 3

        Example return:
            [
                {
                    "id": 1,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Em separação",
                    "products": {
                        "1": {
                            "id": 12,
                            "description": "Refrigerante Cola 2L",
                            "sell_value": 8.99,
                            "barcode": "789100000012",
                            "section_name": "Bebidas",
                            "stock": 110,
                            "expiration_date": "2026-02-01",
                            "images": {
                                "0": "UklGRn..."
                            },
                            "quantity": 5
                        },
                        "2": {
                            "id": 7,
                            "description": "Manteiga com Sal",
                            "sell_value": 8.9,
                            "barcode": "789100000007",
                            "section_name": "Laticínios",
                            "stock": 60,
                            "expiration_date": "2025-12-15",
                            "images": {
                                "0": "UklGRs..."
                            },
                            "quantity": 28
                        }
                        [...]
                    }
                },
                {
                    "id": 2,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Nova",
                    "products": {...}
                }
            ]
                    
    '''
    args = []
    date_field = "o.created_at BETWEEN %s AND %s"
    section_field = ''
    id_field = ''
    order_status_field = ''
    client_id_field = ''
    if start_date != None:
        try:
            start_date = datetime.strptime(start_date, "%d/%m/%Y")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Data de início inválida")
    else:
        start_date = datetime.strptime('01/01/1900', "%d/%m/%Y")
    if end_date != None:
        try:
            end_date = datetime.strptime(end_date, "%d/%m/%Y")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Data de fim inválida")
    else:
        end_date = datetime.now(pytz.timezone('America/Sao_Paulo'))
    start_date = start_date.strftime("%Y-%m-%d") + " 00:00:00+00"
    end_date = end_date.strftime("%Y-%m-%d") + " 23:59:59+00"
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Data de fim início não pode ser maior que data de fim")
    args.append(start_date)
    args.append(end_date)
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        if section != None and section != '':
            try:
                section_id = utils.get_section_id(db_cursor, section)
                section_field = "AND s.id = '%s' "
                args.append(section_id)
            except utils.ObjectNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Categoria não localizada, por favor redefina o filtro")

        if id != None and id > 0:
            id_field = "AND o.id = '%s' "
            args.append(id)

        if order_status != None and order_status != '':
            try:
                order_status_id = utils.get_status_id(db_cursor, order_status)
                order_status_field = "AND o.status = '%s' "
                args.append(order_status_id)
            except utils.ObjectNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status não localizado, por favor redefina o filtro")

        if client_id != None and client_id > 0:
            try:
                client = Client(db_cursor, id = client_id)
                client_id_field = "AND c.id = '%s' "
                args.append(client_id)
            except ObjectNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado, por favor redefina o filtro")
        args.append(offset)
        
        query = f"""
            SELECT o.id
            FROM orders o
            JOIN orders_products op ON o.id = op.order_id
            JOIN products p ON op.product_id = p.id
            JOIN sections s ON p.section_id = s.id
            JOIN clients c ON o.client_id = c.id
            WHERE
            {date_field}
            {section_field}
            {id_field}
            {order_status_field}
            {client_id_field}
            GROUP BY o.id
            LIMIT 20 OFFSET %s;
        """
        query = re.sub('\n+', ' ', query)
        query = re.sub(' +', ' ', query)
        result_raw = db_operations.select(db_cursor, query, args)
        if len(result_raw) == 0:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        result = []
        for entry in result_raw:
            order = Order(db_cursor, entry)
            result.append(order.get_info())
        db_connection.commit()
        return result
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.post("/orders")
async def create_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_order: NewOrder
):
    ''' Registers new order. Returns a success message and the ID of the new order.
    If user_id is not found, returns 400 with detail.
    
    If any item is not found, returns 400 with detail.
    
    If any quantity is bigger than product's stock, returns 400 with detail.
    
    All request values are required, at least one product is required.

        client_id(int): ID of the order's client (postive non-zero).
        products(list): A list of dictionaries containing two key-values pair: 'product_id'(int) and 'quantity'(int).
        
        Example request:
            {
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
            }

        Example return:
            {
                "message": "Ordem criada com sucesso",
                "id": order.id
            }

    '''
    if len(new_order.products)<1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ao menos um item obrigatório")
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            client = Client(db_cursor, new_order.client_id)
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Cliente não localizado")
        
        try:
            product_list = [
                    {
                        'product':Product(db_cursor, x.product_id),
                        'quantity':x.quantity
                    } for x in new_order.products
                ]
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produtos não localizado")
        
        insufficient_items = []
        for item in product_list:
            if item['quantity'] > item['product'].stock:
                insufficient_items.append(
                    {
                        'product_id': item['product'].id,
                        'description': item['product'].description,
                        'stock': item['product'].stock,
                        'requested': item['quantity'],
                        'delta': item['product'].stock - item['quantity']
                    }
                )
        if len(insufficient_items)>0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= {'message':"Um ou mais produtos não possui estoque sucifiente", 'details': insufficient_items})

        query = "INSERT INTO orders (client_id) VALUES (%s)"
        new_id = db_operations.insert(db_cursor, query, (new_order.client_id,), 'id')
        order = Order(db_cursor, new_id)

        for item in product_list:
            order.include_product(item['product'].id, item['quantity'])
        db_connection.commit()
        return {"message": "Ordem criada com sucesso", "id": order.id}
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.get("/orders/{id}")
async def get_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Returns an order by id
    id (int): Order's id to be returned

        Example Return:
            {
                "id": 5,
                "created_at": "2025-05-25T16:29:13.177126+00:00",
                "status": "Cancelada",
                "products": {
                    "1": {
                        "id": 6,
                        "description": "Café Torrado e Moído",
                        "sell_value": 14.5,
                        "barcode": "789100000006",
                        "section_name": "Marcearia",
                        "stock": 90,
                        "expiration_date": "2025-11-05",
                        "images": {
                            "0": "UklGRn..."
                        },
                        "quantity": 4
                    }, 
                    "2": {...},
                    [...]
                }
            }
    '''
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        return Order(db_cursor, id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não localizada")
    finally:
        db_cursor.close()
        db_connection.close()
    
@router.put("/orders/{id}")
async def update_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_info: UpdateOrder
):
    ''' Updates order. Returns the order's detail if successfull.
        
    All request values are optional, but at least one is required.
    
    If new status is "Cancelado", products lists are ignored and all current products in order will be returned to stock.
    
    Orders with status "Cancelado" or "Entregue" cannot be modified.

        status (string, optional, default = None): Must be exact match from order_status table (case insensitive).
        products_to_include (list, optional, default = None): A list of dictionaries of products to be included in order containing two key-values pair:
            'product_id'(int) and 'quantity'(int).
        products_to_remove (list, optional, default = None): A list of dictionaries of products to be removed from order containing two key-values pair:
            'product_id'(int) and 'quantity'(int).

        Example request:
            {
                "id": 10,
                "products_to_include": [
                    {
                        "product_id": 2,
                        "quantity": 10
                    },
                    {
                        "product_id": 5,
                        "quantity": 3
                    }
                ]
            }

        Example return:
            {
                "message": "Ordem atualizada com sucesso",
                "details": {
                    "id": 6,
                    "created_at": "2025-05-25T16:29:13.177126+00:00",
                    "status": "Em transporte",
                    "products": {
                        "1": {
                            "id": 1,
                            "description": "Leite Integral",
                            "sell_value": 4.5,
                            "barcode": "789100000001",
                            "section_name": "Laticínios",
                            "stock": 100,
                            "expiration_date": "2026-05-01",
                            "images": {
                                "0": "UklGRh..."
                            },
                            "quantity": 19
                        },
                        "2": {...},
                        [...]
                    }
                }
            }

    '''
    try:
        order = Order(db_cursor, id)
        if not order.is_open():
            raise OrderCantBeChanged
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status inválido")
    except OrderCantBeChanged:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não pode ser alterada. Verifique se a mesma não está cancelada ou entregue.")
    if new_info.status != None:
        try:
            status_id = utils.get_status_id(db_cursor, new_info.status)
        except utils.ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Status inválido")
        try:
            if status_id == 1:
                order.cancel_order()
                return {"message": "Ordem cancelada com sucesso."}
        except OrderCantBeChanged:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Ordem não pode ser alterada. Verifique se a mesma não está cancelada ou entregue.")
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        if new_info.products_to_include != None:
            try:
                for item in new_info.products_to_include:
                    product = Product(db_cursor, item.product_id)
                    quantity = item.quantity
                    order.include_product(product.id, quantity)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto informado possui quantidade além do disponível no estoque.")
            except ObjectNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não foi localizado")
        if new_info.products_to_remove != None:
            try:
                for item in new_info.products_to_remove:
                    product = Product(db_cursor, item.product_id)
                    quantity = item.quantity
                    order.remove_product(db_cursor, product.id, quantity)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto informado possui quantidade além do disponível na ordem.")
            except ObjectNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não foi localizado")
            except ItemNotFound:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Um ou mais produto não existe na ordem")
        order.change_status(db_cursor, status_id)
        db_connection.commit()
        return {
            "message": "Ordem atualizada com sucesso",
            "details": order.get_info()
        }
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()


@router.delete("/orders/{id}")
async def delete_order(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Deletes order from provided ID. Only admins can perform this action.
    
    If successful, returns success message.
    
    If order is not found, returns 204.

        id: ID of the order to be deleted

        Example return:
            {
                "message": "Ordem deletada com sucesso"
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem deletar ordens")
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            order = Order(db_cursor, id = id)
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        try:
            order.cancel_order()
        except:
            pass
        query = """
            DELETE FROM orders WHERE id = %s
        """
        result = db_operations.insert(db_cursor, query, (id,))
        db_connection.commit()
        return {"message": "Ordem deletada com sucesso"}
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()
