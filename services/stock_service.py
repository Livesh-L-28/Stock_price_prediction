import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from config import Config

class StockService:
    def __init__(self):
        os.makedirs(Config.DATA_DIR, exist_ok=True)

    @staticmethod
    def normalize_ticker(ticker: str, is_indian: bool = False) -> str:
        """Sanitize ticker input and auto-append .NS for Indian stocks if needed."""
        ticker = str(ticker).strip().upper()
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            return ticker
        
        # Check against configured Indian stocks catalog
        indian_bases = {s["symbol"].replace(".NS", "").replace(".BO", ""): s["symbol"] for s in Config.INDIAN_STOCKS}
        if is_indian or ticker in indian_bases:
            return indian_bases.get(ticker, ticker + ".NS")
        return ticker

    @staticmethod
    def get_currency_info(ticker: str) -> dict:
        """Returns appropriate currency symbol and code."""
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            return {"symbol": "₹", "code": "INR"}
        return {"symbol": "$", "code": "USD"}

    def get_cached_filepath(self, ticker: str) -> str:
        safe_ticker = ticker.replace("^", "INDEX_")
        return os.path.join(Config.DATA_DIR, f"{safe_ticker}.csv")

    def is_cache_valid(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        # If cache was modified within CACHE_EXPIRY_HOURS, it is fresh
        return (datetime.now() - mtime) < timedelta(hours=Config.CACHE_EXPIRY_HOURS)

    def fetch_history(self, ticker: str, period: str = "3y", force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch historical stock data with robust caching and header normalization.
        """
        filepath = self.get_cached_filepath(ticker)
        
        if not force_refresh and self.is_cache_valid(filepath):
            try:
                df = pd.read_csv(filepath)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                if len(df) >= 60:
                    return df
            except Exception as e:
                print(f"[StockService] Cache read error for {ticker}: {e}. Refetching...")

        # Fetch from Yahoo Finance
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period)
            
            if df.empty:
                df = yf.download(ticker, period=period, progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()
            if 'Date' not in df.columns and 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'Date'}, inplace=True)

            if 'Close' not in df.columns or df.empty:
                raise ValueError(f"No valid trading data available for ticker '{ticker}'")

            # Clean and normalize types
            df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_localize(None)
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna(subset=['Date', 'Close'])
            df.sort_values('Date', inplace=True)
            
            # Save to cache
            df.to_csv(filepath, index=False)

            df.set_index('Date', inplace=True)
            return df
        except Exception as e:
            print(f"[StockService] Error fetching history for {ticker}: {e}")
            # Try reading old cache if available even if expired
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    return df
                except Exception:
                    pass
            return pd.DataFrame()

    def get_stock_profile(self, ticker: str) -> dict:
        """Fetch real-time quote, fundamentals, and company overview."""
        currency = self.get_currency_info(ticker)
        fallback_profile = {
            "symbol": ticker,
            "name": ticker,
            "currency_symbol": currency["symbol"],
            "currency_code": currency["code"],
            "current_price": 0.0,
            "previous_close": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "day_high": 0.0,
            "day_low": 0.0,
            "open": 0.0,
            "volume": 0,
            "avg_volume": 0,
            "market_cap": "N/A",
            "pe_ratio": "N/A",
            "forward_pe": "N/A",
            "eps": "N/A",
            "fifty_two_week_high": 0.0,
            "fifty_two_week_low": 0.0,
            "dividend_yield": "N/A",
            "beta": "N/A",
            "sector": "N/A",
            "industry": "N/A",
            "summary": "Real-time market asset tracking."
        }

        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            fast_info = getattr(t, "fast_info", None)

            current_price = (
                info.get("currentPrice") or 
                info.get("regularMarketPrice") or 
                (fast_info.last_price if fast_info else None)
            )
            previous_close = (
                info.get("regularMarketPreviousClose") or 
                info.get("previousClose") or 
                (fast_info.previous_close if fast_info else None)
            )

            # If still None, extract from historical data
            if not current_price or not previous_close:
                df = self.fetch_history(ticker, period="5d")
                if not df.empty and len(df) >= 2:
                    current_price = float(df['Close'].iloc[-1])
                    previous_close = float(df['Close'].iloc[-2])
                elif not df.empty:
                    current_price = float(df['Close'].iloc[-1])
                    previous_close = current_price

            current_price = float(current_price) if current_price else 0.0
            previous_close = float(previous_close) if previous_close else current_price
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0.0

            # Format Market Cap
            raw_mc = info.get("marketCap")
            if raw_mc:
                if raw_mc >= 1e12:
                    market_cap = f"{raw_mc / 1e12:.2f} T"
                elif raw_mc >= 1e9:
                    market_cap = f"{raw_mc / 1e9:.2f} B"
                elif raw_mc >= 1e7 and currency["code"] == "INR":
                    market_cap = f"{raw_mc / 1e7:.2f} Cr"
                elif raw_mc >= 1e6:
                    market_cap = f"{raw_mc / 1e6:.2f} M"
                else:
                    market_cap = f"{raw_mc:,}"
            else:
                market_cap = "N/A"

            # Format PE & Dividend
            pe = f"{info.get('trailingPE'):.2f}" if info.get('trailingPE') else "N/A"
            f_pe = f"{info.get('forwardPE'):.2f}" if info.get('forwardPE') else "N/A"
            eps = f"{info.get('trailingEps'):.2f}" if info.get('trailingEps') else "N/A"
            div = f"{info.get('dividendYield') * 100:.2f}%" if info.get('dividendYield') else "N/A"
            beta = f"{info.get('beta'):.2f}" if info.get('beta') else "N/A"

            name = info.get("shortName") or info.get("longName") or ticker
            # Check configured lists for better names
            for stock in Config.INDIAN_STOCKS + Config.US_STOCKS:
                if stock["symbol"] == ticker:
                    name = stock["name"]
                    break

            return {
                "symbol": ticker,
                "name": name,
                "currency_symbol": currency["symbol"],
                "currency_code": currency["code"],
                "current_price": round(current_price, 2),
                "previous_close": round(previous_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "day_high": round(float(info.get("dayHigh") or current_price), 2),
                "day_low": round(float(info.get("dayLow") or current_price), 2),
                "open": round(float(info.get("open") or previous_close), 2),
                "volume": int(info.get("volume") or 0),
                "avg_volume": int(info.get("averageVolume") or 0),
                "market_cap": market_cap,
                "pe_ratio": pe,
                "forward_pe": f_pe,
                "eps": eps,
                "fifty_two_week_high": round(float(info.get("fiftyTwoWeekHigh") or current_price), 2),
                "fifty_two_week_low": round(float(info.get("fiftyTwoWeekLow") or current_price), 2),
                "dividend_yield": div,
                "beta": beta,
                "sector": info.get("sector", "Equities"),
                "industry": info.get("industry", "Financial Asset"),
                "summary": info.get("longBusinessSummary", "No company summary available.")[:350] + "..."
            }
        except Exception as e:
            print(f"[StockService] Error getting profile for {ticker}: {e}")
            return fallback_profile

    def calculate_technicals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates key technical analysis indicators:
        - SMA (20, 50, 200)
        - EMA (12, 26)
        - RSI (14)
        - MACD & Signal Line
        - Bollinger Bands (20-day, 2 std)
        """
        if df.empty or len(df) < 20:
            return df

        df = df.copy()
        close = df['Close']

        # Simple Moving Averages
        df['SMA_20'] = close.rolling(window=20).mean()
        df['SMA_50'] = close.rolling(window=50).mean()
        if len(df) >= 200:
            df['SMA_200'] = close.rolling(window=200).mean()
        else:
            df['SMA_200'] = np.nan

        # Exponential Moving Averages
        df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
        df['EMA_26'] = close.ewm(span=26, adjust=False).mean()

        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Relative Strength Index (RSI 14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        bb_mean = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['BB_Upper'] = bb_mean + (bb_std * 2)
        df['BB_Lower'] = bb_mean - (bb_std * 2)
        df['BB_Middle'] = bb_mean

        # Daily Return & 30-Day Volatility
        df['Daily_Return'] = close.pct_change()
        df['Volatility_30'] = df['Daily_Return'].rolling(window=30).std() * np.sqrt(252) * 100

        return df

    def search(self, query: str) -> list:
        """Search across Indian and US stock catalogs by ticker or company name."""
        if not query:
            return []
        query = query.strip().lower()
        results = []
        all_catalog = [
            {**s, "market": "India 🇮🇳"} for s in Config.INDIAN_STOCKS
        ] + [
            {**s, "market": "US 🇺🇸"} for s in Config.US_STOCKS
        ]
        
        for item in all_catalog:
            if query in item["symbol"].lower() or query in item["name"].lower() or query in item["sector"].lower():
                results.append(item)
                if len(results) >= 8:
                    break
        return results

stock_service = StockService()
