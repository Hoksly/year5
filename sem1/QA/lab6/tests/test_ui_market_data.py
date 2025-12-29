import pytest
from pages.market_page import MarketPage

def test_find_ticker_negative(browser):
    """
    TC-MKT-03: Find Ticker by Scrolling (Negative)
    Verify that a non-existent coin is NOT found after scrolling.
    """
    page = MarketPage(browser)
    page.open()
    
    # We limit scrolls to 2 to make the test faster, 
    # since we know FAKECOIN won't appear.
    is_found = page.find_ticker_by_scrolling("FAKECOIN_123", max_scrolls=2)
    
    assert not is_found, "Unexpectedly found 'FAKECOIN_123' in the list!"