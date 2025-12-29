from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://www.binance.com/en"

    def find(self, locator, time=10):
        return WebDriverWait(self.driver, time).until(EC.presence_of_element_located(locator))

    def wait_for_visibility(self, locator, time=10):
        return WebDriverWait(self.driver, time).until(EC.visibility_of_element_located(locator))

    def wait_for_text(self, locator, text, time=10):
        return WebDriverWait(self.driver, time).until(EC.text_to_be_present_in_element(locator, text))

    def wait_for_clickable(self, locator, time=10):
        return WebDriverWait(self.driver, time).until(EC.element_to_be_clickable(locator))

    def click_if_present(self, locator, time=5):
        """
        Waits for an element to be clickable and clicks it.
        If it doesn't appear within the timeout, does nothing.
        """
        try:
            element = WebDriverWait(self.driver, time).until(EC.element_to_be_clickable(locator))
            element.click()
            return True
        except TimeoutException:
            print("Element not clickable within timeout")
            return False

    def open_url(self, url):
        self.driver.get(url)
