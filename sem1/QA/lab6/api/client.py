import requests

class BinanceAPIClient:
    BASE_URL = "https://api.binance.com/api/v3"

    def get_server_time(self):
        """Реалізація TC-API-01"""
        return requests.get(f"{self.BASE_URL}/time")

    def get_order_book(self, symbol="BTCUSDT", limit=5):
        """Реалізація TC-API-02"""
        params = {"symbol": symbol, "limit": limit}
        return requests.get(f"{self.BASE_URL}/depth", params=params)

    # Примітка: Для приватних запитів (TC-API-03) потрібні API-ключі.
    # В рамках лаби ми можемо емулювати помилку підпису (TC-API-03/05)
    def get_account_info_fake_auth(self):
        """Реалізація TC-API-05 (Bad Signature)"""
        headers = {"X-MBX-APIKEY": "fake_key"}
        params = {"timestamp": 123456789, "signature": "invalid_signature"}
        return requests.get(f"{self.BASE_URL}/account", headers=headers, params=params)
