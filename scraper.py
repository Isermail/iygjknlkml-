from amazon import track_prices
from flipkart import track_flipkart_price
import logging

logging.basicConfig(level=logging.INFO)

async def scrape(url, platform):
    if not url:
        logging.error("URL is None or empty")
        return None, None

    try:
        if platform == "flipkart":
            price, product_name = await track_flipkart_price(url)
        elif platform == "amazon":
            price, product_name = await track_prices(url)
        else:
            raise ValueError("Unsupported platform")

        price_str = str(price) if price is not None else "N/A"
        return product_name, price_str

    except Exception as e:
        logging.error(f"Error scraping product from {platform}: {e}")
        return None, None
