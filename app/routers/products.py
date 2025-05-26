from fastapi import APIRouter
from datetime import datetime
from typing import Annotated, Optional
import re

from fastapi import Depends, HTTPException, status, Query

import db_operations
import utils

from base_models import User, NewProduct, UpdateProduct
from db_classes import ObjectNotFound, Product, admin_role_id

router = APIRouter()

# PRODUCTS ROUTES ------------------------------------------------------------------------------------------------

@router.get("/products")
async def get_products(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    offset: Optional[int] = Query(0, ge=0),
    category: Optional[str] = Query(None),
    sell_value: Optional[float] = Query(0, ge=0),
    available: Optional[bool] = Query(False)
):
    '''Returns products list, limit of 20 entries.
    
        offset (int, optional, default = 0): Sets the offset for the resulting list.
        category (str, optional, default = None): Filter results by section.
        sell_value (float, optional, default = 0): Filter results lower than the specified sell_value if > 0.
        available (bool, optional, default = False): Filter only results with items in stock if True

        Example parameters:
            offset: 10
            category: "Hortifruti"
            sell_value: 10.5
            available: True

        Example return:
            [
                {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                },
                {
                    "id": 4,
                    "description": "Óleo de Soja",
                    "sell_value": 6.9,
                    "barcode": "789100000004",
                    "section_name": "Marcearia",
                    "stock": 120,
                    "expiration_date": "2026-10-06",
                    "images": {
                        "0": "UklGRu..."
                    }
                }
            ]
    '''
    args = []
    category_string = ''
    sell_value_string = ''
    available_string = ''
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        if category != None and category != '':
            try:
                category_id = utils.get_section_id(db_cursor, category)
                category_string = "section_id = %s AND "
                args.append(category_id)
            except ObjectNotFound:
                raise HTTPException(status_code=400, detail= "Categoria não localizada, por favor redefina o filtro")
        
        if sell_value > 0:
            sell_value_string = "sell_value <= %s AND "
            args.append(sell_value)

        if available:
            available_string = "stock > 0 AND "
        
        args.append(offset)
        query = f"""
            SELECT * FROM products {category_string}{sell_value_string}{available_string} LIMIT 20 OFFSET %s
        """
        query = re.sub(' +', ' ', query)
        query = query.replace(" AND LIMIT", " LIMIT")
        if len(category_string+sell_value_string+available_string)>0:
            query = query.replace("FROM products", "FROM products WHERE")
        result_raw = db_operations.select(db_cursor, query, args)
        if len(result_raw) == 0:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        result = []
        for entry in result_raw:
            product = Product(db_cursor, entry[0])
            result.append(product.get_info())
        return result
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.post("/products")
async def create_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    new_product: NewProduct
):
    """ Registers new product. Returns a success message and the ID of the new product.

    Only admins can create products.

    All request fields are required, except for expiration_date and images.

        description (str): Product's description        
        sell_value (float): Product's selling value        
        barcode (str): Product's barcode, must be unique        
        section_id (int): ID of the product's section/category        
        stock (int): Initial stock of the product (must be greater than 0)        
        expiration_date (str, optional, default = None): Products expiration date in format dd/mm/aaaa
        images (list:str, optional, default = None) A list of the product images. Images must be a string in BASE64 encoded format. Headers are optional

        Example request:
                {
                    "description": "A product name/description",
                    "sell_value": 10.50,
                    "barcode": "000000000000000000001",
                    "section_id": 5,
                    "stock": 10,
                    "expiration_date": "01/01/1964"
                    "images": ["UklGRkB7AABXRUJQVlA4IDR7AABw6AOdASqwB...", "UklGRuCRAABXRUJQVlA4INSRA..."]
                }
        Example return:
            {
                "message": "Produto cadastrado com sucesso",
                "detail": {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                }
            }
    """
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem adicionar produtos")
    if new_product.sell_value < .01:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Preço de venda inválido")
    if new_product.stock < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Estoque inicial inválido")
    if new_product.expiration_date != None:
        try:
            date_obj = datetime.strptime(new_product.expiration_date, "%d/%m/%Y")
            new_product.expiration_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Prazo de validade inválido")
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            query = "SELECT id FROM sections where id=%s"
            result = db_operations.select(db_cursor, query, (new_product.section_id,))
            if len(result) < 1:
                raise ObjectNotFound
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "ID de categoria inválido")
        try:
            existing_product = Product(db_cursor, barcode=new_product.barcode)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Código de barras já existe") 
        except ObjectNotFound:
            query = """
                    INSERT INTO products (description, sell_value, barcode, section_id, stock, expiration_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
            args = (
                new_product.description,
                new_product.sell_value,
                new_product.barcode,
                new_product.section_id,
                new_product.stock,
                new_product.expiration_date,
            )
            result = db_operations.insert(db_cursor, query, args, 'id')
            db_connection.commit()
            saved_product = Product(db_cursor, result)
            message = "Produto cadastrado com sucesso"
            errored_image = False
            if new_product.images!=None:
                for image in new_product.images:
                    try:
                        saved_product.insert_image(image)
                    except:
                        if not errored_image:
                            message += ". Uma ou mais imagem não pôde ser salva..."
                            errored_image = True
            db_connection.commit()
            return {
                "message": message,
                "details": saved_product.get_info()
                }
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.get("/products/{id}")
async def get_produc_by_id(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    ''' Returns a product properties identified by id.

    Returns 204 if no product is found.

        id: ID of the product to be searched
        
        Example return:
            {
                "id": 3,
                "description": "Feijão Carioca",
                "sell_value": 8.7,
                "barcode": "789100000003",
                "section_name": "Marcearia",
                "stock": 150,
                "expiration_date": "2025-06-12",
                "images": {
                    "0": "UklGRs..."
                    "1": "UKlGRo..."
                }
            }
    '''
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        return Product(db_cursor, id).get_info()
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Produto não localizado")
    finally:
        db_cursor.close()
        db_connection.close()
    
@router.put("/products/{id}")
async def put_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int,
    new_information: UpdateProduct
):
    ''' Updates a product by id. Only admins can update products.
    
    If successful, returns the updated properties of the product.
    
    Returns 204 if no product is found.
    
    Accepts any property of products to update, except ID which cannot be changed.
    
    All request fields are optional, but at least one is required.

        description (str, default = None): Product's new description
        sell_value (float, default = None): Product's new selling value. (can be 0, but not negative)
        barcode (str, default = None): Product's new barcode, must be unique
        section_id (int, default = None): ID of the product's new section/category
        stock (int, default = None): New initial stock of the product (can be 0, but not negative)
        expiration_date (str, default = None): Products new expiration date in format dd/mm/aaaa
        images (list:str, default = None) A list of the product's new images. Images must be a string in BASE64 encoded format. Headers are optional.
        
        Example request:
                {
                    "description": "A product name/description",
                    "sell_value": 10.50,
                    "barcode": "000000000000000000001",
                    "section_id": 5,
                    "stock": 10,
                    "expiration_date": "01/01/1964"
                    "images": ["UklGRkB7AABXRUJQVlA4IDR7AABw6AOdASqwB...", "UklGRuCRAABXRUJQVlA4INSRA..."]
                }

        Example return:
            {
                "message": "Produto atualizado com sucesso",
                "detail": {
                    "id": 3,
                    "description": "Feijão Carioca",
                    "sell_value": 8.7,
                    "barcode": "789100000003",
                    "section_name": "Marcearia",
                    "stock": 150,
                    "expiration_date": "2025-06-12",
                    "images": {
                        "0": "UklGRs..."
                        "1": "UKlGRo..."
                    }
                }
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem editar productes")
    try:
        product = Product(db_cursor, id = id)
    except ObjectNotFound:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    
    values = []
    description_field = ''
    sell_value_field = ''
    barcode_field = ''
    section_id_field = ''
    stock_field = ''
    expiration_date_field = ''

    if new_information.description != None:
        if new_information.description == '':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Descrição inválida")
        description_field = 'description = %s, '
        values.append(new_information.description)
    
    if new_information.sell_value != None:
        if new_information.sell_value < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Preço de venda inválido")
        sell_value_field = 'sell_value = %s, '
        values.append(new_information.sell_value)
    
    if new_information.barcode != None:
        if new_information.barcode == '':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Barcode inválido")
        try:
            existing_product = Product(db_cursor, barcode=new_information.barcode)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Barcode já existe")
        except ObjectNotFound:
            barcode_field = 'barcode = %s, '
            values.append(new_information.barcode)
    
    if new_information.section_id != None:
        try:
            query = "SELECT * FROM sections WHERE id=%s"
            result = db_operations.select(db_cursor, query, (new_information.section_id,))
            if len(result) < 1:
                raise ObjectNotFound
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "ID de categoria inválido")
        section_id_field = 'section_id = %s, '
        values.append(new_information.section_id)
    
    if new_information.stock != None:
        if new_information.stock < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Estoque inválido")
        stock_field = 'stock = %s, '
        values.append(new_information.stock)

    if new_information.expiration_date != None:
        try:
            date_obj = datetime.strptime(new_information.expiration_date, "%d/%m/%Y")
            new_information.expiration_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Prazo de validade inválido")
        expiration_date_field = 'expiration_date = %s, '
        values.append(new_information.expiration_date)

    query = f"""UPDATE products SET
        {description_field}
        {sell_value_field}
        {barcode_field}
        {section_id_field}
        {stock_field}
        {expiration_date_field} WHERE id = %s """
    query = query.replace('\n', '')
    query = re.sub(' +', ' ', query)
    query = query.replace(", WHERE", " WHERE")
    values.append(id)
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        result = db_operations.insert(db_cursor, query, values, "id")
        updated_product = Product(db_cursor, id = result)
        message = "Produto atualizado com sucesso"
        errored_image = False
        if new_information.images!=None:
            for image in new_information.images:
                try:
                    updated_product.insert_image(image)
                except:
                    if not errored_image:
                        message += ". Uma ou mais imagem não pôde ser salva..."
                        errored_image = True
        db_connection.commit()
        return {
            "message": message,
            "detail": updated_product.get_info()
        }
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()

@router.delete("/products/{id}")
async def delete_product(
    current_user: Annotated[User, Depends(utils.get_current_active_user)],
    id: int
):
    '''Deletes product from provided ID. Only admins can perform this action.
    
    If successful, returns success message.
    
    If product is not found, returns 204.

        id: ID of the product to be deleted

        Example return:
            {
                "message": "Produto deletado com sucesso"
            }
    '''
    if current_user.role > admin_role_id:
        raise HTTPException(status_code=403, detail= "Apenas Admins podem deletar produtos")
    try:
        db_connection = db_operations.postgres_connection();
        db_cursor = db_connection.cursor()
        try:
            if type(id) != int or id<1:
                raise ObjectNotFound
            product = Product(db_cursor, id = id)
        except ObjectNotFound:
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
        query = """
            DELETE FROM products WHERE id = %s
        """
        result = db_operations.insert(db_cursor, query, (id,))
        db_connection.commit()
        return {"message": "Produto deletado com sucesso"}
    except:
        raise
    finally:
        db_cursor.close()
        db_connection.close()
