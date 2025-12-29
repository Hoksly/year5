import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="function")
def browser():
    options = webdriver.ChromeOptions()
    
    # --- VISIBLE MODE ---
    # Comment out the headless line to see the browser UI
    # options.add_argument("--headless=new") 
    
    options.add_argument("--window-size=1920,1080")
    
    # --- CRITICAL LINUX FLAGS ---
    # Keep these! They prevent crashes even in GUI mode on Linux
    options.add_argument("--no-sandbox") 
    options.add_argument("--disable-dev-shm-usage") 
    
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    
    yield driver
    
    # Optional: Keep the browser open for 3 seconds after the test finishes
    # so you can see the final state before it closes.
    time.sleep(3) 
    
    driver.quit()