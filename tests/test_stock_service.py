import pytest
import pandas as pd
import numpy as np
from app import create_app
from services import stock_service, market_service, news_service, ml_service

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

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"

def test_news_sentiment():
    bull_res = news_service._calculate_headline_sentiment("NVIDIA Surges to Record Highs with Strong Profit Growth")
    assert bull_res["label"] == "BULLISH"
    assert bull_res["score"] > 0

    bear_res = news_service._calculate_headline_sentiment("Stock Plunges amid Lawsuit and Revenue Miss")
    assert bear_res["label"] == "BEARISH"
    assert bear_res["score"] < 0

def test_multivariate_feature_extraction():
    # Synthetic dataframe
    dates = pd.date_range("2025-01-01", periods=100)
    df = pd.DataFrame({
        "Open": np.linspace(100, 150, 100),
        "High": np.linspace(102, 153, 100),
        "Low": np.linspace(98, 148, 100),
        "Close": np.linspace(101, 151, 100),
        "Volume": np.random.randint(1000, 5000, 100)
    }, index=dates)

    feat_df = ml_service.extract_multivariate_features(df)
    assert "Close" in feat_df.columns
    assert "Volume" in feat_df.columns
    assert "RSI_14" in feat_df.columns
    assert "MACD" in feat_df.columns
    assert "Spread" in feat_df.columns
    assert len(feat_df.columns) == 5

def test_csv_export(client):
    res = client.get("/stock/AAPL/export-csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["Content-Type"]
    assert b"Date,Open,High,Low,Close,Volume" in res.data

def test_watchlist_quotes_api(client):
    res = client.post("/api/watchlist/quotes", json={"tickers": ["AAPL"]})
    assert res.status_code == 200
    data = res.get_json()
    assert "watchlist" in data
    assert len(data["watchlist"]) > 0
    assert data["watchlist"][0]["symbol"] == "AAPL"
