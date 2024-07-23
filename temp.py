from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Create Chrome options
options = Options()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--incognito')
options.add_argument('--headless')  # Optional: run in headless mode

# Initialize ChromeDriver with options
driver = webdriver.Chrome(options=options)
# Example usage
driver.get("http://www.google.com")
print(driver.title)
driver.quit()