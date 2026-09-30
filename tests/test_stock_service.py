import pytest
from app import create_app
from services import stock_service, market_service

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_ticker_normalization():
    assert stock_service.normalize_ticker("AAPL") == "AAPL"
    assert stock_service.normalize_ticker("reliance") == "RELIANCE.NS"
    assert stock_service.normalize_ticker("TCS.NS") == "TCS.NS"
    assert stock_service.normalize_ticker("infy", is_indian=True) == "INFY.NS"

def test_currency_mapping():
    assert stock_service.get_currency_info("RELIANCE.NS")["symbol"] == "₹"
    assert stock_service.get_currency_info("AAPL")["symbol"] == "$"

def test_market_status_structure():
    status = market_service.get_market_status()
    assert "india" in status
    assert "us" in status
    assert "is_open" in status["india"]
    assert "hours" in status["india"]

def test_search_service():
    results = stock_service.search("Apple")
    assert len(results) > 0
    assert results[0]["symbol"] == "AAPL"

    results_in = stock_service.search("Tata")
    assert len(results_in) > 0

def test_dashboard_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"AlphaPulse" in response.data

def test_market_routes(client):
    res_in = client.get("/market/india")
    assert res_in.status_code == 200
    assert b"National Stock Exchange" in res_in.data

    res_us = client.get("/market/us")
    assert res_us.status_code == 200
    assert b"NYSE" in res_us.data

def test_api_search_endpoint(client):
    response = client.get("/api/search?q=NVDA")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
    assert any(item["symbol"] == "NVDA" for item in data["results"])

def test_legacy_routes_redirect(client):
    res = client.get("/indian")
    assert res.status_code == 302
    assert "/market/india" in res.headers["Location"]
