import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from amazon_config import (
    get_web_driver_options,
    get_chrome_web_driver,
    set_ignore_certificate_error,
    set_browser_as_incognito,
    NAME,
    CURRENCY,
    FILTERS,
    BASE_URL,
    DIRECTORY
)
from selenium.common.exceptions import NoSuchElementException
import json
from datetime import datetime


class GenerateReport:
    def __init__(self, file_name, filters, base_link, currency, data):
        self.data = data
        self.file_name = file_name
        self.filters = filters
        self.base_link = base_link
        self.currency = currency
        report = {
            'title': self.file_name,
            'date': self.get_now(),
            'best_item': self.get_best_item(),
            'currency': self.currency,
            'filters': self.filters,
            'base_link': self.base_link,
            'products': self.data
        }
        print("Creating report...")
        with open(f'{DIRECTORY}/{file_name}.json', 'w') as f:
            json.dump(report, f)
        print("Done...")

    @staticmethod
    def get_now():
        now = datetime.now()
        return now.strftime("%d/%m/%Y %H:%M:%S")

    def get_best_item(self):
        try:
            return sorted(self.data, key=lambda k: k['price'])[0]
        except Exception as e:
            print(e)
            print("Problem with sorting items")
            return None


class AmazonAPI:
    def __init__(self, search_term, filters, base_url, currency):
        self.base_url = base_url
        self.search_term = search_term
        options = get_web_driver_options()
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)
        self.driver = get_chrome_web_driver(options)
        self.currency = currency
        self.price_filter = f"&low-price={filters['min']}&high-price={filters['max']}"
        print(f"Initialized with search term: {self.search_term}, min price: {filters['min']}, max price: {filters['max']}")

    def run(self):
        print("Starting Script...")
        print(f"Looking for {self.search_term} products...")
        links = self.get_products_links()
        if not links:
            print("Stopped script.")
            return
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        products = self.get_products_info(links)
        print(f"Got info about {len(products)} products...")
        self.driver.quit()
        return products

    def get_products_links(self):
        self.driver.get(self.base_url)
        print(f"Navigated to base URL: {self.base_url}")
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="twotabsearchtextbox"]'))
        )
        element.send_keys(self.search_term)
        element.send_keys(Keys.ENTER)
        print(f"Entered search term: {self.search_term}")

        # Wait for the results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 's-main-slot'))
        )
        print("Waited for search results to load")

        # Get the current URL with the price filter
        url_with_filter = f"{self.driver.current_url}{self.price_filter}"
        self.driver.get(url_with_filter)
        print(f"Navigated to URL with price filter: {url_with_filter}")

        # Find the product links by locating divs with class 'a-section' inside 's-main-slot'
        result_list = self.driver.find_elements(By.CLASS_NAME, 's-main-slot')
        links = []
        try:
            # Find all divs with class 'a-section' within the first 's-main-slot'
            a_section_divs = result_list[0].find_elements(By.CSS_SELECTOR, "div.a-section")
            
            # Iterate through each 'a-section' div to find the product links
            for div in a_section_divs:
                # Find all <a> elements within each 'a-section' div
                anchors = div.find_elements(By.TAG_NAME, "a")
                for link in anchors:
                    href = link.get_attribute('href')
                    if href:  # Ensure the href is not None
                        links.append(href)

            print(f"Found {len(links)} product links")
            return links
        except Exception as e:
            print("Didn't get any products...")
            print(e)
            return links

    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    def get_asins(self, links):
        return [self.get_asin(link) for link in links]

    def get_single_product_info(self, asin):
        print(f"Product ID: {asin} - getting data...")
        product_short_url = self.shorten_url(asin)
        print(f"Product URL: {product_short_url}")
        try:
            self.driver.get(f'{product_short_url}?language=en_GB')
            print(f"Navigated to product URL: {product_short_url}")
            title = self.get_title()
            seller = self.get_seller()
            price = self.get_price()
            if title and seller and price:
                product_info = {
                    'asin': asin,
                    'url': product_short_url,
                    'title': title,
                    'seller': seller,
                    'price': price
                }
                print(f"Got product info: {product_info}")
                return product_info
        except Exception as e:
            print(f"Error accessing product URL: {product_short_url}")
            print(e)
        return None

    def get_title(self):
        try:
            title = self.driver.find_element(By.ID, 'productTitle').text
            print(f"Got product title: {title.trim()}")
            return title
        except Exception as e:
            print(e)
            print(f"Can't get title of a product - {self.driver.current_url}")
            return None

    def get_seller(self):
        try:
            seller = self.driver.find_element(By.ID, 'bylineInfo').text
            print(f"Got product seller: {seller.trim()}")
            return seller
        except Exception as e:
            print(e)
            print(f"Can't get seller of a product - {self.driver.current_url}")
            return None
        
    def get_price(self):
        price = None
        try:
            # Locate the main price container
            price_container = self.driver.find_element(By.CLASS_NAME, 'a-price')
            
            # Find the span with class 'a-price-whole'
            whole_price_span = price_container.find_element(By.CLASS_NAME, 'a-price-whole')
            whole_price = whole_price_span.text  # Extract the text from the span
            print(f"Whole price extracted: {whole_price}")

            # Find the span with class 'a-price-decimal' if it exists
            try:
                decimal_price_span = price_container.find_element(By.CLASS_NAME, 'a-price-decimal')
                decimal_price = decimal_price_span.text
                price = f"{whole_price}{decimal_price}"  # Combine whole and decimal parts
                print(f"Decimal price extracted: {decimal_price}")
            except NoSuchElementException:
                price = whole_price  # If no decimal part, just use the whole price

            # Clean up the price string
            price = price.replace(',', '').strip()  # Remove commas and whitespace
            print(f"Final price string: {price}")
            
            # Convert the price to a float if necessary
            price = float(price)  # Convert to float
            return price
        except NoSuchElementException:
            print(f"Price element not found - {self.driver.current_url}")
            return None
        except Exception as e:
            print(e)
            print(f"Can't get price of a product - {self.driver.current_url}")
            return None

    @staticmethod
    def get_asin(product_link):
        return product_link[product_link.find('/dp/') + 4:product_link.find('/ref')]

    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    def convert_price(self, price):
        price = price.split(self.currency)[1]
        try:
            price = price.split("\n")[0] + "." + price.split("\n")[1]
        except:
            pass
        try:
            price = price.split(",")[0] + price.split(",")[1]
        except:
            pass
        return float(price)
    def __init__(self, search_term, filters, base_url, currency):
        self.base_url = base_url
        self.search_term = search_term
        options = get_web_driver_options()
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)
        self.driver = get_chrome_web_driver(options)
        self.currency = currency
        self.price_filter = f"&low-price={filters['min']}&high-price={filters['max']}"
        print(f"Initialized with search term: {self.search_term}, min price: {filters['min']}, max price: {filters['max']}")

    def run(self):
        print("Starting Script...")
        print(f"Looking for {self.search_term} products...")
        links = self.get_products_links()
        if not links:
            print("Stopped script.")
            return
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        products = self.get_products_info(links)
        print(f"Got info about {len(products)} products...")
        self.driver.quit()
        return products

    def get_products_links(self):
        self.driver.get(self.base_url)
        print(f"Navigated to base URL: {self.base_url}")
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="twotabsearchtextbox"]'))
        )
        element.send_keys(self.search_term)
        element.send_keys(Keys.ENTER)
        print(f"Entered search term: {self.search_term}")

        # Wait for the results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 's-main-slot'))
        )
        print("Waited for search results to load")

        # Get the current URL with the price filter
        url_with_filter = f"{self.driver.current_url}{self.price_filter}"
        self.driver.get(url_with_filter)
        print(f"Navigated to URL with price filter: {url_with_filter}")

        # Find the product links starting from the third div with class 's-result-item'
        result_list = self.driver.find_elements(By.CLASS_NAME, 's-main-slot')
        links = []
        try:
            # Use CSS selectors to find h2 elements inside divs with class 's-result-item' starting from the third one
            results = result_list[0].find_elements(By.CSS_SELECTOR, "div.s-result-item:nth-of-type(n+3) h2 a")
            links = [link.get_attribute('href') for link in results]
            print(f"Found {len(links)} product links")
            return links
        except Exception as e:
            print("Didn't get any products...")
            print(e)
            return links

    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    def get_asins(self, links):
        return [self.get_asin(link) for link in links]

    def get_single_product_info(self, asin):
        print(f"Product ID: {asin} - getting data...")
        product_short_url = self.shorten_url(asin)
        print(f"Product URL: {product_short_url}")
        try:
            self.driver.get(f'{product_short_url}?language=en_GB')
            print(f"Navigated to product URL: {product_short_url}")
            title = self.get_title()
            seller = self.get_seller()
            price = self.get_price()
            if title and seller and price:
                product_info = {
                    'asin': asin,
                    'url': product_short_url,
                    'title': title,
                    'seller': seller,
                    'price': price
                }
                print(f"Got product info: {product_info}")
                return product_info
        except Exception as e:
            print(f"Error accessing product URL: {product_short_url}")
            print(e)
        return None

    def get_title(self):
        try:
            title = self.driver.find_element(By.ID, 'productTitle').text
            print(f"Got product title: {title}")
            return title
        except Exception as e:
            print(e)
            print(f"Can't get title of a product - {self.driver.current_url}")
            return None

    def get_seller(self):
        try:
            seller = self.driver.find_element(By.ID, 'bylineInfo').text
            print(f"Got product seller: {seller}")
            return seller
        except Exception as e:
            print(e)
            print(f"Can't get seller of a product - {self.driver.current_url}")
            return None

    def get_price(self):
        price = None
        try:
            price = self.driver.find_element(By.ID, 'priceblock_ourprice').text
            price = self.convert_price(price)
            print(f"Got product price: {price}")
        except NoSuchElementException:
            try:
                availability = self.driver.find_element(By.ID, 'availability').text
                if 'Available' in availability:
                    price = self.driver.find_element(By.CLASS_NAME, 'olp-padding-right').text
                    price = price[price.find(self.currency):]
                    price = self.convert_price(price)
                    print(f"Got product price: {price}")
            except Exception as e:
                print(e)
                print(f"Can't get price of a product - {self.driver.current_url}")
                return None
        except Exception as e:
            print(e)
            print(f"Can't get price of a product - {self.driver.current_url}")
            return None
        return price

    @staticmethod
    def get_asin(product_link):
        return product_link[product_link.find('/dp/') + 4:product_link.find('/ref')]

    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    def convert_price(self, price):
        price = price.split(self.currency)[1]
        try:
            price = price.split("\n")[0] + "." + price.split("\n")[1]
        except:
            pass
        try:
            price = price.split(",")[0] + price.split(",")[1]
        except:
            pass
        return float(price)
    
    def __init__(self, search_term, filters, base_url, currency):
        self.base_url = base_url
        self.search_term = search_term
        options = get_web_driver_options()
        set_ignore_certificate_error(options)
        set_browser_as_incognito(options)
        self.driver = get_chrome_web_driver(options)
        self.currency = currency
        self.price_filter = f"&low-price={filters['min']}&high-price={filters['max']}"
        print(f"Initialized with search term: {self.search_term}, min price: {filters['min']}, max price: {filters['max']}")

    def run(self):
        print("Starting Script...")
        print(f"Looking for {self.search_term} products...")
        links = self.get_products_links()
        if not links:
            print("Stopped script.")
            return
        print(f"Got {len(links)} links to products...")
        print("Getting info about products...")
        products = self.get_products_info(links)
        print(f"Got info about {len(products)} products...")
        self.driver.quit()
        return products

    def get_products_links(self):
        self.driver.get(self.base_url)
        print(f"Navigated to base URL: {self.base_url}")
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="twotabsearchtextbox"]'))
        )
        element.send_keys(self.search_term)
        element.send_keys(Keys.ENTER)
        print(f"Entered search term: {self.search_term}")

        # Wait for the results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 's-main-slot'))
        )
        print("Waited for search results to load")

        # Get the current URL with the price filter
        url_with_filter = f"{self.driver.current_url}{self.price_filter}"
        self.driver.get(url_with_filter)
        print(f"Navigated to URL with price filter: {url_with_filter}")

        # Find the product links
        result_list = self.driver.find_elements(By.CLASS_NAME, 's-main-slot')
     
        links = []
        try:
            results = result_list[0].find_elements(By.CSS_SELECTOR, "div.a-section h2 a")
            links = [link.get_attribute('href') for link in results]
            print(f"Found {len(links)} product links")
            return links
        except Exception as e:
            print("Didn't get any products...")
            print(e)
            return links

    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    def get_asins(self, links):
        return [self.get_asin(link) for link in links]

    def get_single_product_info(self, asin):
        print(f"Product ID: {asin} - getting data...")
        product_short_url = self.shorten_url(asin)
        print(f"Product URL: {product_short_url}")
        try:
            self.driver.get(f'{product_short_url}?language=en_GB')
            print(f"Navigated to product URL: {product_short_url}")
            title = self.get_title()
            seller = self.get_seller()
            price = self.get_price()
            if title and seller and price:
                product_info = {
                    'asin': asin,
                    'url': product_short_url,
                    'title': title,
                    'seller': seller,
                    'price': price
                }
                print(f"Got product info: {product_info}")
                return product_info
        except Exception as e:
            print(f"Error accessing product URL: {product_short_url}")
            print(e)
        return None

    def get_title(self):
        try:
            title = self.driver.find_element(By.ID, 'productTitle').text
            print(f"Got product title: {title}")
            return title
        except Exception as e:
            print(e)
            print(f"Can't get title of a product - {self.driver.current_url}")
            return None

    def get_seller(self):
        try:
            seller = self.driver.find_element(By.ID, 'bylineInfo').text
            print(f"Got product seller: {seller}")
            return seller
        except Exception as e:
            print(e)
            print(f"Can't get seller of a product - {self.driver.current_url}")
            return None

    def get_price(self):
        price = None
        try:
            price = self.driver.find_element(By.ID, 'priceblock_ourprice').text
            price = self.convert_price(price)
            print(f"Got product price: {price}")
        except NoSuchElementException:
            try:
                availability = self.driver.find_element(By.ID, 'availability').text
                if 'Available' in availability:
                    price = self.driver.find_element(By.CLASS_NAME, 'olp-padding-right').text
                    price = price[price.find(self.currency):]
                    price = self.convert_price(price)
                    print(f"Got product price: {price}")
            except Exception as e:
                print(e)
                print(f"Can't get price of a product - {self.driver.current_url}")
                return None
        except Exception as e:
            print(e)
            print(f"Can't get price of a product - {self.driver.current_url}")
            return None
        return price

    @staticmethod
    def get_asin(product_link):
        return product_link[product_link.find('/dp/') + 4:product_link.find('/ref')]

    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    def convert_price(self, price):
        price = price.split(self.currency)[1]
        try:
            price = price.split("\n")[0] + "." + price.split("\n")[1]
        except:
            pass
        try:
            price = price.split(",")[0] + price.split(",")[1]
        except:
            pass
        return float(price)


if __name__ == '__main__':
    am = AmazonAPI(NAME, FILTERS, BASE_URL, CURRENCY)
    data = am.run()
    GenerateReport(NAME, FILTERS, BASE_URL, CURRENCY, data)