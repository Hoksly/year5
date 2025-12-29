import time
from .base_page import BasePage
from .locators import MarketPageLocators
from selenium.common.exceptions import TimeoutException

class MarketPage(BasePage):
    
    def open(self):
        self.open_url(f"{self.base_url}/markets/overview")
        self.handle_cookies()

    def handle_cookies(self):
        # This will now work because click_if_present is fixed in BasePage
        self.click_if_present(MarketPageLocators.COOKIE_ACCEPT_BTN, time=5)

    def find_ticker_by_scrolling(self, target_ticker, max_scrolls=5):
        print(f"DEBUG: Starting search for {target_ticker}...")
        
        for i in range(max_scrolls):
            try:
                # Wait for rows to be visible
                self.wait_for_visibility(MarketPageLocators.MARKET_ROW, time=5)
                rows = self.driver.find_elements(*MarketPageLocators.MARKET_ROW)
            except TimeoutException:
                print("DEBUG: No rows found. Page might be loading or locator is wrong.")
                return False

            # Extract text
            row_texts = [r.text for r in rows]
            
            # Check for the ticker
            for text in row_texts:
                # 'BTC' is usually the first part of the string "BTC\nBitcoin..."
                # using split() ensures we match the exact symbol
                if target_ticker in text.split('\n'):
                    print(f"DEBUG: Found {target_ticker}!")
                    return True
            
            # Scroll down if not found
            print(f"DEBUG: {target_ticker} not found in scroll {i+1} ({len(rows)} rows checked). Scrolling...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 

        return False