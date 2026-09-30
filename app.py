import os
import io
import csv
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import numpy as np

from config import Config
from services import stock_service, ml_service, market_service, news_service

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("alphapulse")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Production Rate Limiter
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["300 per day", "100 per hour"],
        storage_uri="memory://"
    )

    # Context processor to inject market ribbon data into all templates
    @app.context_processor
    def inject_global_market_context():
        try:
            status = market_service.get_market_status()
            indices = market_service.get_market_indices()
        except Exception as e:
            logger.warning(f"Market context error: {e}")
            status, indices = {}, []
        return dict(market_status=status, market_indices=indices)

    # 📌 Health Check for Render & Cloud Monitors
    @app.route("/health")
    @app.route("/healthz")
    def health_check():
        return jsonify({"status": "healthy", "service": "AlphaPulse AI"}), 200

    # 📌 Home Dashboard
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            active_page="home",
            featured_indian=Config.INDIAN_STOCKS,
            featured_us=Config.US_STOCKS
        )

    # 📌 Indian Market Explorer
    @app.route("/market/india")
    def market_india():
        status = market_service.get_market_status()["india"]
        return render_template(
            "market.html",
            active_page="indian",
            market_name="NSE (National Stock Exchange)",
            market_title="Indian Equities (NSE)",
            market_flag="🇮🇳",
            stocks=Config.INDIAN_STOCKS,
            status=status
        )

    # 📌 US Market Explorer
    @app.route("/market/us")
    def market_us():
        status = market_service.get_market_status()["us"]
        return render_template(
            "market.html",
            active_page="us",
            market_name="US Equities (NYSE / NASDAQ)",
            market_title="US Equities (NYSE/NASDAQ)",
            market_flag="🇺🇸",
            stocks=Config.US_STOCKS,
            status=status
        )

    # 📌 Deep-Dive Stock Analysis
    @app.route("/stock/<ticker>")
    def stock_detail(ticker):
        ticker = stock_service.normalize_ticker(ticker)
        profile = stock_service.get_stock_profile(ticker)
        
        # Historical prices & technicals for interactive candlestick chart
        df = stock_service.fetch_history(ticker, period="1y")
        if df.empty or len(df) < 20:
            return render_template(
                "error.html",
                error_title=f"Insufficient Market Data for '{ticker}'",
                error_message="The selected equity symbol does not have sufficient recent trading history to render technical analysis charts."
            ), 404

        df_tech = stock_service.calculate_technicals(df)
        
        # Serialize candlestick payload for Plotly
        dates = [d.strftime('%Y-%m-%d') for d in df_tech.index]
        chart_payload = {
            "dates": dates,
            "opens": [round(float(x), 2) for x in df_tech['Open'].values],
            "highs": [round(float(x), 2) for x in df_tech['High'].values],
            "lows": [round(float(x), 2) for x in df_tech['Low'].values],
            "closes": [round(float(x), 2) for x in df_tech['Close'].values],
            "volumes": [int(x) for x in df_tech['Volume'].values],
            "sma20": [round(float(x), 2) if not np.isnan(x) else None for x in df_tech['SMA_20'].values],
            "sma50": [round(float(x), 2) if not np.isnan(x) else None for x in df_tech['SMA_50'].values]
        }

        # Latest technical indicators snapshot
        latest = df_tech.iloc[-1]
        technicals = {
            "rsi": round(float(latest['RSI_14']), 1) if not np.isnan(latest.get('RSI_14', np.nan)) else "N/A",
            "macd": round(float(latest['MACD']), 2) if not np.isnan(latest.get('MACD', np.nan)) else "N/A",
            "macd_signal": round(float(latest['MACD_Signal']), 2) if not np.isnan(latest.get('MACD_Signal', np.nan)) else "N/A",
            "bb_upper": round(float(latest['BB_Upper']), 2) if not np.isnan(latest.get('BB_Upper', np.nan)) else "N/A",
            "bb_lower": round(float(latest['BB_Lower']), 2) if not np.isnan(latest.get('BB_Lower', np.nan)) else "N/A",
            "sma_20": round(float(latest['SMA_20']), 2) if not np.isnan(latest.get('SMA_20', np.nan)) else "N/A",
            "sma_50": round(float(latest['SMA_50']), 2) if not np.isnan(latest.get('SMA_50', np.nan)) else "N/A",
            "sma_200": round(float(latest['SMA_200']), 2) if not np.isnan(latest.get('SMA_200', np.nan)) else "N/A",
            "volatility": round(float(latest['Volatility_30']), 2) if not np.isnan(latest.get('Volatility_30', np.nan)) else "N/A"
        }

        # Real-time News & Financial Sentiment
        news_data = news_service.get_stock_news(ticker)

        return render_template(
            "stock.html",
            active_page="stock",
            profile=profile,
            technicals=technicals,
            chart_payload=chart_payload,
            news=news_data
        )

    # 📌 Deep Learning Prediction Endpoint (Rate Limited to 15 requests per minute)
    @app.route("/predict", methods=["GET", "POST"])
    @limiter.limit("15 per minute")
    def predict():
        if request.method == "GET":
            ticker = request.args.get("ticker", "AAPL")
            try:
                days = int(request.args.get("days", 30))
            except ValueError:
                days = 30
            force_retrain = request.args.get("force_retrain", "false").lower() == "true"
        else:
            ticker = request.form.get("ticker", "").strip()
            try:
                days = int(request.form.get("days", 30))
            except ValueError:
                days = 30
            force_retrain = request.form.get("force_retrain") == "true"

        if not ticker:
            return redirect(url_for("index"))

        ticker = stock_service.normalize_ticker(ticker)
        currency_info = stock_service.get_currency_info(ticker)

        # Retrieve historical training dataset
        df = stock_service.fetch_history(ticker, period="3y")
        if df.empty or len(df) < Config.LOOKBACK_WINDOW + 20:
            return render_template(
                "error.html",
                error_title=f"Could not load data for symbol '{ticker}'",
                error_message="Yahoo Finance returned no historical price series or the asset was recently listed. Please verify the ticker."
            ), 400

        # Execute Multivariate Machine Learning pipeline
        result = ml_service.run_prediction_pipeline(
            ticker=ticker,
            df=df,
            forecast_days=days,
            force_retrain=force_retrain
        )

        if not result.get("success"):
            return render_template(
                "error.html",
                error_title="Model Execution Failed",
                error_message=f"Deep learning pipeline could not complete: {result.get('error')}"
            ), 500

        profile = stock_service.get_stock_profile(ticker)
        news_data = news_service.get_stock_news(ticker, max_items=4)

        return render_template(
            "predict.html",
            active_page="predict",
            result=result,
            company_name=profile["name"],
            currency_symbol=currency_info["symbol"],
            news=news_data
        )

    # 📌 Export Stock Data & Technicals to CSV
    @app.route("/stock/<ticker>/export-csv")
    def export_stock_csv(ticker):
        ticker = stock_service.normalize_ticker(ticker)
        df = stock_service.fetch_history(ticker, period="1y")
        
        if df.empty:
            return "No data found to export.", 404

        df_tech = stock_service.calculate_technicals(df)

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume", "SMA_20", "SMA_50", "RSI_14", "MACD", "BB_Upper", "BB_Lower"])

        for dt, row in df_tech.iterrows():
            writer.writerow([
                dt.strftime('%Y-%m-%d'),
                round(float(row.get('Open', 0)), 2),
                round(float(row.get('High', 0)), 2),
                round(float(row.get('Low', 0)), 2),
                round(float(row.get('Close', 0)), 2),
                int(row.get('Volume', 0)),
                round(float(row.get('SMA_20', 0)), 2) if not np.isnan(row.get('SMA_20', np.nan)) else "",
                round(float(row.get('SMA_50', 0)), 2) if not np.isnan(row.get('SMA_50', np.nan)) else "",
                round(float(row.get('RSI_14', 0)), 2) if not np.isnan(row.get('RSI_14', np.nan)) else "",
                round(float(row.get('MACD', 0)), 2) if not np.isnan(row.get('MACD', np.nan)) else "",
                round(float(row.get('BB_Upper', 0)), 2) if not np.isnan(row.get('BB_Upper', np.nan)) else "",
                round(float(row.get('BB_Lower', 0)), 2) if not np.isnan(row.get('BB_Lower', np.nan)) else ""
            ])

        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={ticker}_historical_analytics.csv"
        return response

    # 📌 Real-time Training Progress API
    @app.route("/api/train-progress/<ticker>")
    def train_progress(ticker):
        ticker = stock_service.normalize_ticker(ticker)
        status = ml_service.training_status.get(ticker, {"status": "idle", "progress_pct": 100})
        return jsonify(status)

    # 📌 Real-Time Watchlist Batch Quotes API
    @app.route("/api/watchlist/quotes", methods=["POST"])
    def watchlist_quotes():
        data = request.get_json() or {}
        tickers = data.get("tickers", [])
        results = []
        for sym in tickers[:15]:
            try:
                sym_norm = stock_service.normalize_ticker(sym)
                prof = stock_service.get_stock_profile(sym_norm)
                results.append({
                    "symbol": sym_norm,
                    "name": prof["name"],
                    "price": prof["current_price"],
                    "change": prof["change"],
                    "change_percent": prof["change_percent"],
                    "currency_symbol": prof["currency_symbol"]
                })
            except Exception:
                continue
        return jsonify({"watchlist": results})

    # 📌 Backward Compatibility Routes
    @app.route("/indian")
    def legacy_indian():
        return redirect(url_for("market_india"))

    @app.route("/us")
    def legacy_us():
        return redirect(url_for("market_us"))

    @app.route("/predict_indian", methods=["POST"])
    def legacy_predict_indian():
        ticker = request.form.get("ticker", "")
        days = request.form.get("days", 30)
        ticker = stock_service.normalize_ticker(ticker, is_indian=True)
        return redirect(url_for("predict", ticker=ticker, days=days))

    @app.route("/predict_us", methods=["POST"])
    def legacy_predict_us():
        ticker = request.form.get("ticker", "")
        days = request.form.get("days", 30)
        ticker = stock_service.normalize_ticker(ticker, is_indian=False)
        return redirect(url_for("predict", ticker=ticker, days=days))

    # 📌 REST APIs for Autocomplete & Data Fetching
    @app.route("/api/search")
    def api_search():
        q = request.args.get("q", "")
        results = stock_service.search(q)
        return jsonify({"results": results})

    @app.route("/api/stock/<ticker>")
    def api_stock_profile(ticker):
        ticker = stock_service.normalize_ticker(ticker)
        profile = stock_service.get_stock_profile(ticker)
        return jsonify(profile)

    # 📌 Global Error Handlers
    @app.errorhandler(429)
    def rate_limit_error(error):
        return render_template(
            "error.html",
            error_title="429 - Rate Limit Cooldown",
            error_message="To ensure fair compute allocation across all users, ML prediction requests are capped at 15 per minute. Please pause for a few seconds before generating another forecast."
        ), 429

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template(
            "error.html",
            error_title="404 - Page Not Found",
            error_message="The requested financial analytics page or equity symbol could not be located."
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template(
            "error.html",
            error_title="500 - Internal Service Error",
            error_message="The financial analytics server encountered an internal condition. Please try again shortly."
        ), 500

    return app

# WSGI Entry Application Instance
app = create_app()

if __name__ == "__main__":
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    os.makedirs(Config.MODELS_DIR, exist_ok=True)
    
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"🚀 AlphaPulse AI Production Server running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
