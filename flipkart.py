from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import logging

def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_service = Service(r'C:\Users\mahes\Downloads\chromedriver-win64\chromedriver.exe')  # Update the path to chromedriver
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    return driver

def scrape_with_selenium(url):
    driver = setup_selenium()
    driver.get(url)
    html = driver.page_source
    driver.quit()
    return html

async def track_flipkart_price(url):
    try:
        html = scrape_with_selenium(url)
        soup = BeautifulSoup(html, 'lxml')

        product_name_tag = soup.find("span", class_="B_NuCI")
        product_name = product_name_tag.get_text(strip=True) if product_name_tag else "Unknown Product"

        price_tag = soup.find("div", class_="_30jeq3 _16Jk6d")
        if price_tag:
            price_text = price_tag.get_text(strip=True).replace(',', '').replace('₹', '').strip()

            try:
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
