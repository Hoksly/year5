This project contains automated tests for the Binance platform, covering both UI and API functionalities.

## Structure

- `api/`: Contains the API client for interacting with the Binance API.
- `pages/`: Contains Page Object models for UI tests.
- `tests/`: Contains the actual test cases for both UI and API.
- `conftest.py`: Fixtures for tests (e.g., WebDriver setup).
- `requirements.txt`: Project dependencies.
- `pytest.ini`: Pytest configuration.

## How to run tests

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run tests:
    ```bash
    pytest tests/ -v --html=report.html
    ```
