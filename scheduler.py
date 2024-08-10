import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
from scraper import scrape
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

dbclient = AsyncIOMotorClient(os.getenv("MONGO_URI"))
database = dbclient[os.getenv("DATABASE")]
collection = database[os.getenv("COLLECTION")]
PRODUCTS = database[os.getenv("PRODUCTS")]

async def convert_price(price):
    if isinstance(price, str):
        return float(price.replace(',', '').replace('₹', '').strip())
    elif isinstance(price, (int, float)):
        return float(price)
    else:
        raise ValueError(f"Unsupported price format: {price}")

async def check_prices(app):
    logging.info("Checking Price for Products...")
    async for product in PRODUCTS.find():
        try:
            product_name, current_price = await scrape(product["url"], "amazon" if "amazon" in product["url"] else "flipkart")
            await asyncio.sleep(1)

            if current_price is not None:
                try:
                    current_price = await convert_price(current_price)
                    previous_price = await convert_price(product.get("price", "0"))
                except ValueError as e:
                    logging.error(f"Could not convert price to float: {e}")
                    continue

                if current_price != previous_price:
                    await PRODUCTS.update_one(
                        {"_id": product["_id"]},
                        {
                            "$set": {
                                "price": current_price,
                                "previous_price": previous_price,
                                "lower": min(current_price, float(product.get("lower", current_price))),
                                "upper": max(current_price, float(product.get("upper", current_price))),
                            }
                        },
                    )
                    logging.info(f"Price updated for {product_name}: {previous_price} -> {current_price}")
        except Exception as e:
            logging.error(f"Error checking price for product {product['url']}: {e}")

    logging.info("Completed")
    changed_products = await compare_prices()

    for changed_product in changed_products:
        cursor = collection.find({"product_id": changed_product})
        users = await cursor.to_list(length=None)

        for user in users:
            product = await PRODUCTS.find_one({"_id": user.get("product_id")})
            if product:
                try:
                    current_price = await convert_price(product["price"])
                    previous_price = await convert_price(product["previous_price"])

                    percentage_change = ((current_price - previous_price) / previous_price) * 100

                    text = (
                        f"🎉 Good news! The price of {product['product_name']} has changed.\n"
                        f" - Previous Price: ₹{previous_price:.2f}\n"
                        f" - Current Price: ₹{current_price:.2f}\n"
                        f" - Percentage Change: {percentage_change:.2f}%\n"
                        f" - [Check it out here]({product['url']})"
                    )

                    await app.send_message(
                        chat_id=user.get("user_id"), text=text, disable_web_page_preview=True
                    )
                except ValueError as e:
                    logging.error(f"Error calculating percentage change: {e}")

async def compare_prices():
    logging.info("Comparing Prices...")
    product_with_changes = []

    async for product in PRODUCTS.find():
        try:
            current_price = await convert_price(product.get("price", "0"))
            previous_price = await convert_price(product.get("previous_price", "0"))
        except ValueError as e:
            logging.error(f"Error converting prices: {e}")
            continue

        if current_price != previous_price:
            product_with_changes.append(product.get("_id"))

    return product_with_changes
