from selenium.webdriver.common.by import By

from selenium.webdriver.common.by import By

class MarketPageLocators:
    # 1. Primary Strategy: Use the specific class for rows in the market table
    MARKET_ROW = (By.CSS_SELECTOR, "div.css-vlibs4")
    
    # 2. Backup Strategy: If the class changes, use this XPath which finds rows by structure
    # (Matches any div that is a direct child of the market list container)
    # MARKET_ROW = (By.XPATH, "//div[contains(@class, 'css-')]/div[contains(@class, 'css-') and .//div[text()='BTC']]/..")

    # The ticker text inside the row (e.g. "BTC")
    # This class is for the symbol text specifically
    TICKER_SYMBOL = (By.CSS_SELECTOR, ".css-17wnpgm") 
    
    # Cookie Banner
    COOKIE_ACCEPT_BTN = (By.ID, "onetrust-accept-btn-handler")

class TradePageLocators:
    # Chart often uses canvas or iframe
    CHART_CONTAINER = (By.CSS_SELECTOR, "div[data-testid='chart-container'], iframe, canvas, .chart-container")
    
    
    # Order book usually has a specific structure, looking for list items or divs with price classes
    ORDER_BOOK = (By.CSS_SELECTOR, "div[data-testid='order-book'], .orderbook-container, .order-book-container, div[class*='orderBook']")
    
    # Use XPath for text matching
    BUY_BUTTON = (By.XPATH, "//button[@data-testid='trade-buy-button' or contains(text(), 'Buy') or contains(@class, 'buy')]")
    SELL_BUTTON = (By.XPATH, "//button[@data-testid='trade-sell-button' or contains(text(), 'Sell') or contains(@class, 'sell')]")
    
    # Price is usually large and changing
    CURRENT_PRICE = (By.CSS_SELECTOR, ".showPrice, div[data-testid='current-price'], div[class*='currentPrice']")
