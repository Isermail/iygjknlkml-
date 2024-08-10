import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import logging

# Setup User-Agent rotation and Selenium
ua = UserAgent()

def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_service = Service(r'C:\Users\mahes\Downloads\chromedriver-win64\chromedriver.exe')  # Update the path to chromedriver
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    return driver

def scrape_with_selenium(url):
    driver = setup_selenium()
    driver.get(url)
    html = driver.page_source
    driver.quit()
    return html

async def track_prices(url):
    try:
        html = scrape_with_selenium(url)  # Use Selenium to get the full HTML

        soup = BeautifulSoup(html, 'lxml')

        # Extract the product name
        product_name_tag = soup.find(id="productTitle")
        product_name = product_name_tag.get_text(strip=True) if product_name_tag else "Unknown Product"

        # Extract the price
        price_tag = soup.find("span", class_="a-price-whole")
        if price_tag:
            # Clean the price string
            price_text = price_tag.get_text(strip=True).replace(',', '').replace('₹', '').strip()
            price_fraction_tag = soup.find("span", class_="a-price-fraction")
            if price_fraction_tag:
                price_text += "." + price_fraction_tag.get_text(strip=True).strip()

            try:
                # Convert the cleaned price string to float
                price_float = float(price_text)
                return price_float, product_name
            except ValueError as e:
                logging.error(f"Value conversion failed: {e}")
                return None, product_name
        else:
            logging.warning("No price elements found")
            return None, product_name

    except Exception as e:
        logging.error(f"Error scraping product: {e}")
        return None, None
