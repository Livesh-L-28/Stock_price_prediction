import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Production configuration for Stock Predictor."""
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-secret-stock-ai-prediction-key-2026")
    DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    MODELS_DIR = os.getenv("MODELS_DIR", str(BASE_DIR / "models"))
    
    # Cache settings
    CACHE_EXPIRY_HOURS = int(os.getenv("CACHE_EXPIRY_HOURS", "12"))
    LIVE_CACHE_MINUTES = int(os.getenv("LIVE_CACHE_MINUTES", "15"))
    
    # ML Hyperparameters
    LOOKBACK_WINDOW = 60
    DEFAULT_FORECAST_DAYS = 30
    MAX_FORECAST_DAYS = 90
    MIN_FORECAST_DAYS = 1
    LSTM_EPOCHS = 15
    LSTM_BATCH_SIZE = 32
    
    # Market Indices
    INDICES = {
        "NIFTY 50": "^NSEI",
        "BSE SENSEX": "^BSESN",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW JONES": "^DJI"
    }

    # Curated Top 50 Indian Stocks with Company Names & Sectors
    INDIAN_STOCKS = [
        {"symbol": "RELIANCE.NS", "name": "Reliance Industries Ltd", "sector": "Energy & Conglomerate"},
        {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "sector": "Information Technology"},
        {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "sector": "Financial Services"},
        {"symbol": "INFY.NS", "name": "Infosys Ltd", "sector": "Information Technology"},
        {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "sector": "Financial Services"},
        {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Ltd", "sector": "Consumer Goods"},
        {"symbol": "ITC.NS", "name": "ITC Ltd", "sector": "Consumer Goods"},
        {"symbol": "SBIN.NS", "name": "State Bank of India", "sector": "Financial Services"},
        {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "sector": "Telecommunications"},
        {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "sector": "Financial Services"},
        {"symbol": "LT.NS", "name": "Larsen & Toubro Ltd", "sector": "Construction & Engineering"},
        {"symbol": "AXISBANK.NS", "name": "Axis Bank Ltd", "sector": "Financial Services"},
        {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Ltd", "sector": "Financial Services"},
        {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
        {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries", "sector": "Healthcare & Pharma"},
        {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "sector": "Automobile"},
        {"symbol": "TATASTEEL.NS", "name": "Tata Steel Ltd", "sector": "Metals & Mining"},
        {"symbol": "HCLTECH.NS", "name": "HCL Technologies Ltd", "sector": "Information Technology"},
        {"symbol": "NTPC.NS", "name": "NTPC Ltd", "sector": "Power & Energy"},
        {"symbol": "ONGC.NS", "name": "Oil & Natural Gas Corp", "sector": "Energy"},
        {"symbol": "WIPRO.NS", "name": "Wipro Ltd", "sector": "Information Technology"},
        {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Ltd", "sector": "Commodities & Infra"},
        {"symbol": "ADANIPORTS.NS", "name": "Adani Ports & SEZ Ltd", "sector": "Infrastructure"},
        {"symbol": "TITAN.NS", "name": "Titan Company Ltd", "sector": "Consumer Discretionary"},
        {"symbol": "POWERGRID.NS", "name": "Power Grid Corp of India", "sector": "Utilities"},
        {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Ltd", "sector": "Materials"},
        {"symbol": "COALINDIA.NS", "name": "Coal India Ltd", "sector": "Energy & Mining"},
        {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv Ltd", "sector": "Financial Services"},
        {"symbol": "ASIANPAINT.NS", "name": "Asian Paints Ltd", "sector": "Consumer Goods"},
        {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories", "sector": "Healthcare & Pharma"},
        {"symbol": "CIPLA.NS", "name": "Cipla Ltd", "sector": "Healthcare & Pharma"},
        {"symbol": "GRASIM.NS", "name": "Grasim Industries Ltd", "sector": "Materials & Textiles"},
        {"symbol": "JSWSTEEL.NS", "name": "JSW Steel Ltd", "sector": "Metals & Mining"},
        {"symbol": "HINDALCO.NS", "name": "Hindalco Industries Ltd", "sector": "Metals & Mining"},
        {"symbol": "TECHM.NS", "name": "Tech Mahindra Ltd", "sector": "Information Technology"},
        {"symbol": "EICHERMOT.NS", "name": "Eicher Motors Ltd", "sector": "Automobile"},
        {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Ltd", "sector": "Healthcare & Pharma"},
        {"symbol": "BPCL.NS", "name": "Bharat Petroleum Corp", "sector": "Energy & Refining"},
        {"symbol": "BRITANNIA.NS", "name": "Britannia Industries Ltd", "sector": "Consumer Goods"},
        {"symbol": "BEL.NS", "name": "Bharat Electronics Ltd", "sector": "Aerospace & Defence"},
        {"symbol": "M&M.NS", "name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
        {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank Ltd", "sector": "Financial Services"},
        {"symbol": "PIDILITIND.NS", "name": "Pidilite Industries Ltd", "sector": "Chemicals"},
        {"symbol": "HDFCLIFE.NS", "name": "HDFC Life Insurance Co", "sector": "Insurance"},
        {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance Co", "sector": "Insurance"},
        {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "sector": "Financial Services"},
        {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products", "sector": "Consumer Goods"},
        {"symbol": "GAIL.NS", "name": "GAIL (India) Ltd", "sector": "Utilities & Gas"},
        {"symbol": "SHREECEM.NS", "name": "Shree Cement Ltd", "sector": "Materials"},
        {"symbol": "COLPAL.NS", "name": "Colgate-Palmolive India", "sector": "Consumer Goods"}
    ]

    # Curated Top 50 US Stocks with Company Names & Sectors
    US_STOCKS = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Consumer Electronics"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Software & Cloud"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Semiconductors & AI"},
        {"symbol": "GOOGL", "name": "Alphabet Inc. (Google)", "sector": "Internet & Search"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "E-Commerce & Cloud"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Social Media & Tech"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Automotive & Clean Energy"},
        {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "sector": "Financial Holding"},
        {"symbol": "AVGO", "name": "Broadcom Inc.", "sector": "Semiconductors"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Banking & Finance"},
        {"symbol": "LLY", "name": "Eli Lilly and Company", "sector": "Pharmaceuticals"},
        {"symbol": "V", "name": "Visa Inc.", "sector": "Payments & Financial"},
        {"symbol": "UNH", "name": "UnitedHealth Group", "sector": "Healthcare & Insurance"},
        {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy & Oil"},
        {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Retail"},
        {"symbol": "MA", "name": "Mastercard Inc.", "sector": "Payments & Financial"},
        {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Pharmaceuticals & Healthcare"},
        {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Goods"},
        {"symbol": "COST", "name": "Costco Wholesale Corp", "sector": "Retail"},
        {"symbol": "HD", "name": "The Home Depot Inc.", "sector": "Home Improvement"},
        {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Biotechnology"},
        {"symbol": "BAC", "name": "Bank of America Corp", "sector": "Banking & Finance"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Entertainment & Streaming"},
        {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Enterprise Software"},
        {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Enterprise Software & Cloud"},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "sector": "Semiconductors"},
        {"symbol": "KO", "name": "The Coca-Cola Company", "sector": "Beverages"},
        {"symbol": "PEP", "name": "PepsiCo Inc.", "sector": "Beverages & Snacks"},
        {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy & Oil"},
        {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Creative Software"},
        {"symbol": "QCOM", "name": "QUALCOMM Inc.", "sector": "Semiconductors & Telecom"},
        {"symbol": "TMO", "name": "Thermo Fisher Scientific", "sector": "Life Sciences"},
        {"symbol": "CSCO", "name": "Cisco Systems Inc.", "sector": "Networking Equipment"},
        {"symbol": "MCD", "name": "McDonald's Corporation", "sector": "Restaurants"},
        {"symbol": "INTU", "name": "Intuit Inc.", "sector": "Financial Software"},
        {"symbol": "IBM", "name": "International Business Machines", "sector": "IT & Cloud Services"},
        {"symbol": "GE", "name": "General Electric Company", "sector": "Industrial Conglomerate"},
        {"symbol": "CAT", "name": "Caterpillar Inc.", "sector": "Heavy Machinery"},
        {"symbol": "TXN", "name": "Texas Instruments Inc.", "sector": "Semiconductors"},
        {"symbol": "AMGN", "name": "Amgen Inc.", "sector": "Biotechnology"},
        {"symbol": "DIS", "name": "The Walt Disney Company", "sector": "Entertainment & Media"},
        {"symbol": "SBUX", "name": "Starbucks Corporation", "sector": "Restaurants & Coffee"},
        {"symbol": "INTC", "name": "Intel Corporation", "sector": "Semiconductors"},
        {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Digital Payments"},
        {"symbol": "UBER", "name": "Uber Technologies Inc.", "sector": "Mobility & Delivery"},
        {"symbol": "NKE", "name": "NIKE Inc.", "sector": "Footwear & Apparel"},
        {"symbol": "LOW", "name": "Lowe's Companies Inc.", "sector": "Home Improvement"},
        {"symbol": "HON", "name": "Honeywell International", "sector": "Industrial Automation"},
        {"symbol": "UPS", "name": "United Parcel Service", "sector": "Logistics & Transport"},
        {"symbol": "BLK", "name": "BlackRock Inc.", "sector": "Asset Management"}
    ]
