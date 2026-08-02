from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Flask
import matplotlib.pyplot as plt
import io
import base64
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import os
from tqdm import tqdm

app = Flask(__name__)

# 📌 Make sure data folder exists
os.makedirs("data", exist_ok=True)

# 📌 Expanded stock lists (50 Indian + 50 US stocks)
indian_stocks = [
    "RELIANCE.NS", "TATASTEEL.NS", "INFY.NS", "HDFCBANK.NS", "LUXIND.NS",
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "HCLTECH.NS", "ITC.NS",
    "TCS.NS", "MARUTI.NS", "LT.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "JSWSTEEL.NS", "SUNPHARMA.NS", "WIPRO.NS", "HINDUNILVR.NS", "BAJFINANCE.NS",
    "TECHM.NS", "DRREDDY.NS", "ADANIPORTS.NS", "ONGC.NS", "NTPC.NS",
    "VEDL.NS", "UPL.NS", "BPCL.NS", "GRASIM.NS", "COALINDIA.NS",
    "SBILIFE.NS", "DIVISLAB.NS", "EICHERMOT.NS", "TITAN.NS", "CIPLA.NS",
    "ULTRACEMCO.NS", "ICICIPRULI.NS", "BAJAJ-AUTO.NS", "M&M.NS", "BEL.NS",
    "HINDALCO.NS", "INDUSINDBK.NS", "BRITANNIA.NS", "PIDILITIND.NS", "HDFCLIFE.NS",
    "SHREECEM.NS", "COLPAL.NS", "GAIL.NS", "TATACONSUM.NS", "BANKBARODA.NS"
]

us_stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NVDA", "BRK-B", "JNJ", "V",
    "JPM", "PG", "DIS", "MA", "HD",
    "NFLX", "KO", "PEP", "BAC", "XOM",
    "ABBV", "ADBE", "CRM", "CSCO", "ORCL",
    "INTC", "CMCSA", "NKE", "WMT", "MCD",
    "PYPL", "QCOM", "COST", "AVGO", "ACN",
    "TXN", "AMGN", "HON", "UNH", "UPS",
    "IBM", "MDLZ", "LIN", "RTX", "SBUX",
    "INTU", "GE", "CAT", "DE", "BLK"
]

all_stocks = indian_stocks + us_stocks

# 📌 Helper to download single stock data cleanly
def fetch_stock_data(ticker, period="3y"):
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
        return df
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        return None

# 📌 Download & cache all stocks
def download_and_cache_stocks():
    print("\nDownloading all stocks for caching...")
    for ticker in tqdm(all_stocks):
        filepath = f"data/{ticker}.csv"
        if os.path.exists(filepath):
            continue  # already cached
        df = fetch_stock_data(ticker)
        if df is not None and not df.empty and 'Close' in df.columns:
            df.to_csv(filepath, index=False)
    print("\n✅ Finished caching stocks.")

# 📌 Load stock from cached CSV
def load_stock_data(ticker, max_retries=3):
    import time
    filepath = f"data/{ticker}.csv"

    # Retry download if missing or corrupted
    for attempt in range(max_retries):
        if not os.path.exists(filepath):
            try:
                df = fetch_stock_data(ticker)
                if df is not None and not df.empty and 'Close' in df.columns:
                    df.to_csv(filepath, index=False)
                else:
                    raise ValueError("No valid stock data returned")
            except Exception as e:
                print(f"Attempt {attempt+1} failed for {ticker}: {e}")
                time.sleep(2)
                continue

        # Load CSV safely
        try:
            df = pd.read_csv(filepath)
            
            # Handle possible MultiIndex format from old cached files
            if 'Close' not in df.columns:
                df = pd.read_csv(filepath, header=[0, 1])
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            
            if 'Close' not in df.columns:
                raise ValueError("No Close column in CSV")

            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

            date_col = 'Date' if 'Date' in df.columns else df.columns[0]
            df['Date'] = pd.to_datetime(df[date_col], errors='coerce', utc=True)
            df = df.dropna(subset=['Date', 'Close'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)

            if len(df) < 60:
                raise ValueError(f"Insufficient data ({len(df)} rows) for 60-day sequence")

            return df[['Close']]
        except Exception as e:
            print(f"Error loading {ticker}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            time.sleep(2)
            continue
    return None



# 📌 Prepare data for LSTM
def prepare_data(data, time_step=60):
    scaler = MinMaxScaler(feature_range=(0,1))
    data_scaled = scaler.fit_transform(data)

    X, Y = [], []
    for i in range(len(data_scaled) - time_step):
        X.append(data_scaled[i:i+time_step])
        Y.append(data_scaled[i+time_step])
    
    return np.array(X), np.array(Y), scaler

# 📌 Train LSTM model
def train_lstm(X_train, Y_train):
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(60, 1)),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25),
        Dense(1)
    ])
    
    model.compile(optimizer="adam", loss="mean_squared_error")
    model.fit(X_train, Y_train, epochs=10, batch_size=32, verbose=0)
    
    return model

# 📌 Predict next days
def predict_next_days(model, data, scaler, days=30):
    last_60_days = data[-60:].values
    scaled_data = scaler.transform(last_60_days)

    predictions = []
    for _ in range(days):
        X_input = scaled_data[-60:].reshape(1, 60, 1)
        pred = model.predict(X_input, verbose=0)
        predictions.append(pred[0][0])
        scaled_data = np.append(scaled_data, pred)[1:].reshape(-1, 1)

    return scaler.inverse_transform(np.array(predictions).reshape(-1, 1))

# 📌 Home page
@app.route("/")
def home():
    return render_template("index.html")

# 📌 Indian stock page
@app.route("/indian")
def indian_stocks_page():
    return render_template("indian.html")

# 📌 US stock page
@app.route("/us")
def us_stocks_page():
    return render_template("us.html")

# 📌 Prediction function
def predict_stock(indian=False):
    ticker = request.form["ticker"].upper().strip()
    days = int(request.form["days"])

    if indian and not (ticker.endswith(".NS") or ticker.endswith(".BO")):
        ticker += ".NS"

    stock_data = load_stock_data(ticker)
    if stock_data is None:
        return f"Error: No stock data found for {ticker}. Please check the symbol and try again."

    X_train, Y_train, scaler = prepare_data(stock_data)
    model = train_lstm(X_train, Y_train)

    predicted_prices = predict_next_days(model, stock_data[['Close']], scaler, days=days)
    future_dates = pd.date_range(start=stock_data.index[-1], periods=days+1, freq='B')[1:]

    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.index, stock_data['Close'], color='red', label="Actual Price")
    plt.plot(future_dates, predicted_prices, color='blue', label="Predicted Price")
    plt.xlabel("Time")
    plt.ylabel(f"{ticker} Stock Price")
    plt.title(f"{ticker} Stock Price Prediction")
    plt.legend()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return render_template("predict.html", 
                           ticker=ticker, 
                           predicted_price=round(predicted_prices[-1][0], 2), 
                           plot_url=plot_url)

# 📌 Prediction routes
@app.route("/predict_indian", methods=["POST"])
def predict_indian():
    return predict_stock(indian=True)

@app.route("/predict_us", methods=["POST"])
def predict_us():
    return predict_stock(indian=False)

# 📌 Run app
if __name__ == "__main__":
    download_and_cache_stocks()  # Pre-download 100+ stocks
    app.run(debug=True)
