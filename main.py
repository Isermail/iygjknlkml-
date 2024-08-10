#main.py

from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
import os
import re
import asyncio
import schedule
from pymongo import MongoClient
import datetime
import time
import threading
import requests
import json
import logging
from scraper import scrape
from scheduler import check_prices
from helpers import fetch_all_products, add_new_product, fetch_one_product, delete_one
from regex_patterns import flipkart_patterns, amazon_patterns, all_url_patterns

# Load environment variables
load_dotenv()

# Get environment variables
bot_token = os.getenv("BOT_TOKEN")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
EARNKARO_API_TOKEN = os.getenv("EARNKARO_API_TOKEN")

# MongoDB connection
dbclient = MongoClient(os.getenv("MONGO_URI"))
database = dbclient[os.getenv("DATABASE")]
users_collection = database["Users"]

LOG_CHANNEL_ID = -1002206093759  # Replace with your log channel ID
ADMINS = [1720819569]  # Replace with actual admin user ID(s)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to log new users
async def log_new_user(user_id, username):
    user = {
        "user_id": user_id,
        "username": username,
        "joined_at": datetime.datetime.now(datetime.timezone.utc)
    }

    existing_user = users_collection.find_one({"user_id": user_id})
    if not existing_user:
        users_collection.insert_one(user)
        return True
    return False

# Initialize the bot
app = Client("PriceTrackerBot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Function to expand short URLs
def expand_short_url(short_url):
    try:
        response = requests.head(short_url, allow_redirects=True)
        return response.url
    except Exception as e:
        logging.error(f"Error expanding URL: {e}")
        return None

# Function to convert links to affiliate links using EarnKaro API
async def convert_to_affiliate_link(url):
    api_url = "https://ekaro-api.affiliaters.in/api/converter/public"
    payload = json.dumps({
        "deal": url,
        "convert_option": "convert_only"
    })
    headers = {
        'Authorization': f'Bearer {EARNKARO_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    try:
        logging.info(f"Converting URL: {url}")
        response = requests.post(api_url, headers=headers, data=payload)
        response_data = response.json()
        logging.info(f"Response Data: {response_data}")
        if response.status_code == 200 and response_data.get("success") == 1:
            return response_data.get("data")
        else:
            logging.error(f"Conversion failed: {response_data.get('message')}")
            return None
    except Exception as e:
        logging.error(f"Error converting link: {e}")
        return None

# Function to extract URLs from text
def extract_urls(text):
    return re.findall(r'https?://\S+', text)

@app.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Log new user to MongoDB and notify in the log channel
    is_new_user = await log_new_user(user_id, username)
    if is_new_user:
        await app.send_message(LOG_CHANNEL_ID, f"New user started the bot: @{username} (ID: {user_id})")

    text = (
        f"Hello {username}! 🌟\n\n"
        "I'm PriceTrackerBot, your personal assistant for tracking product prices. 💸\n\n"
        "To get started, use the /my_trackings command to start tracking a product. "
        "Simply send the URL:\n"
        "For example:\n"
        "I'll keep you updated on any price changes for the products you're tracking. "
        "Feel free to ask for help with the /help command at any time. Happy tracking! 🚀"
    )

    await message.reply_text(text, quote=True)

@app.on_message(filters.command("help") & filters.private)
async def help(_, message: Message):
    text = (
        "Here are the commands you can use with PriceTrackerBot:\n\n"
        "/start - Start the bot and get a welcome message.\n"
        "/my_trackings - Get a list of products you're tracking.\n"
        "/product [ID] - Get details about a specific product.\n"
        "/stop [ID] - Stop tracking a specific product.\n"
        "/broadcast - Send a message to all users (admin only).\n"
        "/help - Show this help message.\n\n"
        "To start tracking a product, just send the product link. I'll handle the rest!"
    )
    await message.reply_text(text)

@app.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast(bot, message):
    users = users_collection.find()
    b_msg = message.reply_to_message
    total_users = users_collection.count_documents({})
    success = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(user["user_id"], b_msg.text.markdown)
            success += 1
        except Exception as e:
            logging.error(f"Failed to send message to {user['user_id']}: {e}")
            failed += 1
        await asyncio.sleep(1)  # Avoid hitting rate limits

    await message.reply_text(f"Broadcast completed:\nSuccess: {success}\nFailed: {failed}")

@app.on_message(filters.command("my_trackings") & filters.private)
async def track(_, message):
    try:
        chat_id = message.chat.id
        text = await message.reply_text("Fetching Your Products...")
        products = await fetch_all_products(chat_id)

        if products:
            products_message = "Your Tracked Products:\n\n"
            for i, product in enumerate(products, start=1):
                _id = product.get("product_id")
                product_name = product.get("product_name")
                product_url = product.get("url")
                product_price = product.get("price")

                products_message += (
                    f"🏷️ **Product {i}**: [{product_name}]({product_url})\n\n"
                    f"💰 **Current Price**: {product_price}\n"
                    f"❌ Use /stop {_id} to Stop tracking\n\n"
                )

            await text.edit(products_message, disable_web_page_preview=True)
        else:
            await text.edit("No products added yet")
    except Exception as e:
        logging.error(f"Error fetching products: {e}")

@app.on_message(filters.regex("|".join(all_url_patterns)) | filters.photo | filters.document)
async def track_product_url(_, message: Message):
    try:
        # Send initial status message
        status = await message.reply_text("Analysing Your Product... Please Wait!!")

        if message.photo or message.document:
            # Notify the user to send only links
            await message.reply_text("Please send only links, not images or documents.")
            return

        # Extract URLs from text messages
        urls = extract_urls(message.text)
        if not urls:
            await message.reply_text("Please send only links, not images or documents.")
            return

        for url in urls:
            # Expand short URLs
            if any(re.match(pattern, url) for pattern in flipkart_patterns + amazon_patterns):
                expanded_url = expand_short_url(url)
            else:
                expanded_url = url

            if not expanded_url:
                await message.reply_text("Failed to expand the short URL.")
                continue

            # Determine platform
            platform = "amazon" if any(re.match(pattern, expanded_url) for pattern in amazon_patterns) else "flipkart"

            # Convert to affiliate link using EarnKaro
            affiliate_link = await convert_to_affiliate_link(expanded_url)
            if not affiliate_link:
                await message.reply_text("Failed to convert link to affiliate link.")
                continue

            expanded_url = affiliate_link

            # Scrape product details
            product_name, price = await scrape(expanded_url, platform)
            if product_name and price:
                id = await add_new_product(message.chat.id, product_name, expanded_url, price)
                await status.edit(
                    f'Tracking your product "{product_name}"!\n\n'
                    f"You can use\n /product_{id} to get more information about it."
                )
            else:
                await status.edit("Failed to scrape!!!")

        # Wait for 5 seconds before deleting the user's message
        await asyncio.sleep(5)
        await message.delete()
    except Exception as e:
        logging.error(f"Error tracking product URL: {e}")
        await status.edit("An error occurred while processing your request.")

@app.on_message(filters.command("stop") & filters.private)
async def delete_product(_, message: Message):
    try:
        # Check if the message contains the command and an ID
        if len(message.text.split('_')) < 2:
            await message.reply_text("Please provide a product ID. Usage: /stop [ID]")
            return

        __, id = message.text.split('_')
        status = await message.reply_text("Removing Product...")

        result = await delete_one(id, message.chat.id)
        if result:
            await status.edit("Product successfully removed.")
        else:
            await status.edit("Product not found or already removed.")
    except Exception as e:
        logging.error(f"Error removing product: {e}")
        await status.edit("An error occurred while processing your request. Please try again later.")

# Scheduled task to check prices periodically
async def scheduled_check_prices():
    while True:
        await check_prices(app)
        await asyncio.sleep(3600)  # Check prices every hour

def main():
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_check_prices())
    app.run()

if __name__ == "__main__":
    main()