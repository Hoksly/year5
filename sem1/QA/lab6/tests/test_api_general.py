from api.client import BinanceAPIClient

client = BinanceAPIClient()

def test_api_server_time():
    """
    TC-API-01: Public API: Час сервера
    Очікуваний результат: Status 200, наявність serverTime
    """
    response = client.get_server_time()
    assert response.status_code == 200
    assert "serverTime" in response.json()

def test_api_order_book():
    """
    TC-API-02: Public API: Глибина стакану
    Очікуваний результат: Status 200, масиви bids/asks
    """
    response = client.get_order_book(symbol="BTCUSDT", limit=5)
    data = response.json()
    assert response.status_code == 200
    assert "bids" in data
    assert "asks" in data
    assert len(data["bids"]) == 5

def test_api_auth_error():
    """
    TC-API-05: Security: Помилка автентифікації
    Очікуваний результат: Status 401 (або 400), msg про підпис
    """
    response = client.get_account_info_fake_auth()
    # Binance може повертати 400 або 401 для поганого підпису
    assert response.status_code in [400, 401] 
