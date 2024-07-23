from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

DIRECTORY = 'reports'
NAME = 'PS4'
CURRENCY = '₹'
MIN_PRICE = '20000'
MAX_PRICE = '25000'
FILTERS = {
    'min': MIN_PRICE,
    'max': MAX_PRICE
}
BASE_URL = "http://www.amazon.in/"

def get_chrome_web_driver(options):
    # Automatically download and install ChromeDriver
    service = Service(ChromeDriverManager().install())  # Create a Service object
    return webdriver.Chrome(service=service, options=options)  # Pass the service and options

def get_web_driver_options():
    return webdriver.ChromeOptions()

def set_ignore_certificate_error(options):
    options.add_argument('--ignore-certificate-errors')

def set_browser_as_incognito(options):
    options.add_argument('--incognito')

def set_automation_as_head_less(options):
    options.add_argument('--headless')