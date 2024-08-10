from motor.motor_asyncio import AsyncIOMotorClient
import os
from bson import ObjectId
import logging

dbclient = AsyncIOMotorClient(os.getenv("MONGO_URI"))
database = dbclient[os.getenv("DATABASE")]
collection = database[os.getenv("COLLECTION")]
PRODUCTS = database[os.getenv("PRODUCTS")]

async def fetch_all_products(user_id):
    try:
        cursor = collection.find({"user_id": user_id})
        products = await cursor.to_list(length=None)

        global_products = []
        for product in products:
            global_product = await PRODUCTS.find_one({"_id": product.get("product_id")})
            if global_product:
                global_product["product_id"] = product.get("_id")
                global_products.append(global_product)

        return global_products

    except Exception as e:
        logging.error(f"Error fetching products: {str(e)}")
        return []

async def fetch_one_product(_id):
    try:
        product = await collection.find_one({"_id": ObjectId(_id)})
        if product:
            global_product = await PRODUCTS.find_one({"_id": product.get("product_id")})
            return global_product, None  # Return the product and None for error
        else:
            logging.warning(f"Product with ID {_id} not found.")
            return None, None  # Return None for both values

    except Exception as e:
        logging.error(f"Error fetching product: {str(e)}")
        return None, None  # Return None for both values

async def add_new_product(user_id, product_name, product_url, initial_price):
    try:
        existing_global_product = await PRODUCTS.find_one({"product_name": product_name})
        if not existing_global_product:
            global_new_product = {
                "product_name": product_name,
                "url": product_url,
                "price": initial_price,
                "previous_price": initial_price,
                "upper": initial_price,
                "lower": initial_price,
            }
            insert_result = await PRODUCTS.insert_one(global_new_product)
            existing_global_product = {"_id": insert_result.inserted_id}

        existing_product = await collection.find_one(
            {"user_id": user_id, "product_id": existing_global_product["_id"]}
        )

        if existing_product:
            logging.info("Product already exists.")
            return existing_product["_id"]

        new_local_product = {
            "user_id": user_id,
            "product_id": existing_global_product["_id"],
        }

        result = await collection.insert_one(new_local_product)

        logging.info("Product added successfully.")
        return result.inserted_id

    except Exception as e:
        logging.error(f"Error adding product: {str(e)}")
        return None

async def delete_one(_id, user_id):
    try:
        product = await collection.find_one({"_id": ObjectId(_id)})

        if product and product.get("user_id") == int(user_id):
            await collection.delete_one({"_id": ObjectId(_id)})
            return True
        else:
            logging.warning(f"Product with ID {_id} not found or user ID mismatch.")
            return None

    except Exception as e:
        logging.error(f"Error deleting product: {str(e)}")
        return None
