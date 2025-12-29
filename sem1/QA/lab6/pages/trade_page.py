from .base_page import BasePage
from .locators import TradePageLocators

class TradePage(BasePage):

    def open(self, symbol="BTC_USDT"):
        # Binance URL structure for spot trading: /en/trade/BTC_USDT
        self.open_url(f"{self.base_url}/trade/{symbol}")

    def is_chart_visible(self):
        try:
            return self.wait_for_visibility(TradePageLocators.CHART_CONTAINER, time=5).is_displayed()
        except:
            return False

    def is_order_book_visible(self):
        try:
            return self.wait_for_visibility(TradePageLocators.ORDER_BOOK, time=5).is_displayed()
        except:
            return False

    def get_current_price(self):
        try:
            return self.wait_for_visibility(TradePageLocators.CURRENT_PRICE, time=5).text
        except:
            return None
