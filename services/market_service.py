from datetime import datetime, timezone
import pytz
import yfinance as yf
from config import Config

class MarketService:
    @staticmethod
    def get_market_status() -> dict:
        """Determines whether NSE (India) and NYSE (US) are open or closed."""
        now_utc = datetime.now(timezone.utc)
        
        # India Market (Asia/Kolkata: 09:15 - 15:30 Mon-Fri)
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = now_utc.astimezone(ist)
        is_ist_weekday = now_ist.weekday() < 5
        ist_time = now_ist.time()
        ist_open_time = datetime.strptime("09:15", "%H:%M").time()
        ist_close_time = datetime.strptime("15:30", "%H:%M").time()
        india_open = is_ist_weekday and (ist_open_time <= ist_time <= ist_close_time)

        # US Market (America/New_York: 09:30 - 16:00 Mon-Fri)
        est = pytz.timezone('America/New_York')
        now_est = now_utc.astimezone(est)
        is_est_weekday = now_est.weekday() < 5
        est_time = now_est.time()
        est_open_time = datetime.strptime("09:30", "%H:%M").time()
        est_close_time = datetime.strptime("16:00", "%H:%M").time()
        us_open = is_est_weekday and (est_open_time <= est_time <= est_close_time)

        return {
            "india": {
                "name": "NSE / BSE (India)",
                "is_open": india_open,
                "current_time": now_ist.strftime("%H:%M:%S IST"),
                "hours": "09:15 - 15:30 IST",
                "badge_class": "bg-success" if india_open else "bg-secondary"
            },
            "us": {
                "name": "NYSE / NASDAQ (US)",
                "is_open": us_open,
                "current_time": now_est.strftime("%H:%M:%S EST"),
                "hours": "09:30 - 16:00 EST",
                "badge_class": "bg-success" if us_open else "bg-secondary"
            }
        }

    @staticmethod
    def get_market_indices() -> list:
        """Fetch real-time snapshots of major benchmark indices."""
        results = []
        for name, symbol in Config.INDICES.items():
            try:
                t = yf.Ticker(symbol)
                # fast_info is rapid and low-overhead
                fast = getattr(t, "fast_info", None)
                if fast and fast.last_price:
                    price = fast.last_price
                    prev = fast.previous_close or price
                else:
                    hist = t.history(period="5d")
                    if not hist.empty and len(hist) >= 2:
                        price = float(hist['Close'].iloc[-1])
                        prev = float(hist['Close'].iloc[-2])
                    elif not hist.empty:
                        price = float(hist['Close'].iloc[-1])
                        prev = price
                    else:
                        price, prev = 0.0, 0.0

                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                
                currency = "₹" if "NSE" in name or "SENSEX" in name else "$"
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": f"{price:,.2f}",
                    "change": f"{'+' if change >= 0 else ''}{change:,.2f}",
                    "change_pct": f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%",
                    "is_positive": change >= 0,
                    "currency": currency
                })
            except Exception as e:
                print(f"[MarketService] Index {name} fetch error: {e}")
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": "--",
                    "change": "0.00",
                    "change_pct": "0.00%",
                    "is_positive": True,
                    "currency": ""
                })
        return results

market_service = MarketService()
