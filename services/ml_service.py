import os
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
from config import Config

class MLService:
    def __init__(self):
        os.makedirs(Config.MODELS_DIR, exist_ok=True)

    def _get_model_path(self, ticker: str) -> str:
        safe_ticker = ticker.replace("^", "INDEX_").replace(".", "_")
        return os.path.join(Config.MODELS_DIR, f"{safe_ticker}.keras")

    def is_model_fresh(self, model_path: str, max_age_days: int = 7) -> bool:
        if not os.path.exists(model_path):
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(model_path))
        return (datetime.now() - mtime) < timedelta(days=max_age_days)

    def prepare_dataset(self, series: np.ndarray, time_step: int = 60):
        """Creates sliding sequence windows for LSTM."""
        X, y = [], []
        for i in range(len(series) - time_step):
            X.append(series[i:i + time_step])
            y.append(series[i + time_step])
        return np.array(X), np.array(y)

    def build_lstm_model(self, input_shape: tuple = (60, 1)) -> Sequential:
        """Constructs an optimized Stacked LSTM architecture."""
        model = Sequential([
            Input(shape=input_shape),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation="relu"),
            Dense(1)
        ])
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mean_squared_error")
        return model

    def train_or_load_model(self, ticker: str, scaled_train: np.ndarray, force_retrain: bool = False):
        """Loads cached model if fresh; otherwise trains and persists a new one."""
        model_path = self._get_model_path(ticker)
        
        if not force_retrain and self.is_model_fresh(model_path):
            try:
                print(f"[MLService] Loading cached model for {ticker} from {model_path}...")
                model = load_model(model_path)
                return model, "Cached (Instant)"
            except Exception as e:
                print(f"[MLService] Failed loading model {model_path}: {e}. Retraining...")

        # Train new model
        print(f"[MLService] Training fresh LSTM model for {ticker}...")
        X_train, y_train = self.prepare_dataset(scaled_train, time_step=Config.LOOKBACK_WINDOW)
        
        if len(X_train) == 0:
            raise ValueError("Insufficient training samples for sequence generation.")

        model = self.build_lstm_model(input_shape=(Config.LOOKBACK_WINDOW, 1))
        
        # Train with early stopping if needed
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=3, restore_best_weights=True)
        model.fit(
            X_train, 
            y_train, 
            epochs=Config.LSTM_EPOCHS, 
            batch_size=Config.LSTM_BATCH_SIZE, 
            verbose=0,
            callbacks=[early_stop]
        )

        try:
            model.save(model_path)
            print(f"[MLService] Successfully saved model to {model_path}")
        except Exception as e:
            print(f"[MLService] Could not save model: {e}")

        return model, "Trained Fresh"

    def run_prediction_pipeline(self, ticker: str, df: pd.DataFrame, forecast_days: int = 30, force_retrain: bool = False) -> dict:
        """
        Complete end-to-end production pipeline:
        1. Preprocessing & scaling
        2. Train/Test split for evaluation
        3. Model loading or training
        4. Test set backtesting & real metrics (RMSE, MAE, MAPE, Directional Accuracy)
        5. Future forecasting with confidence intervals
        """
        try:
            if df.empty or len(df) < Config.LOOKBACK_WINDOW + 20:
                raise ValueError(f"Need at least {Config.LOOKBACK_WINDOW + 20} historical days. Found {len(df)}.")

            forecast_days = max(Config.MIN_FORECAST_DAYS, min(forecast_days, Config.MAX_FORECAST_DAYS))
            
            close_prices = df[['Close']].values.astype(float)
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(close_prices)

            # Split: Reserve the last 40 days as test/validation set for realistic backtesting
            test_size = min(40, int(len(scaled_data) * 0.15))
            train_size = len(scaled_data) - test_size
            
            scaled_train = scaled_data[:train_size]
            
            # Train or retrieve model
            model, model_status = self.train_or_load_model(ticker, scaled_train, force_retrain=force_retrain)

            # Backtesting on the test set
            # Construct sequences for test evaluation
            test_inputs = scaled_data[len(scaled_data) - test_size - Config.LOOKBACK_WINDOW:]
            X_test = []
            for i in range(Config.LOOKBACK_WINDOW, len(test_inputs)):
                X_test.append(test_inputs[i - Config.LOOKBACK_WINDOW:i])
            X_test = np.array(X_test)

            if len(X_test) > 0:
                scaled_test_preds = model.predict(X_test, verbose=0)
                test_preds = scaler.inverse_transform(scaled_test_preds).flatten()
                actual_test = close_prices[train_size:].flatten()
                
                # Align lengths
                min_len = min(len(test_preds), len(actual_test))
                test_preds = test_preds[:min_len]
                actual_test = actual_test[:min_len]

                rmse = float(np.sqrt(mean_squared_error(actual_test, test_preds)))
                mae = float(mean_absolute_error(actual_test, test_preds))
                mape = float(np.mean(np.abs((actual_test - test_preds) / (actual_test + 1e-6))) * 100)
                r2 = float(r2_score(actual_test, test_preds))
                
                # Directional accuracy
                if min_len > 1:
                    actual_dir = np.diff(actual_test) > 0
                    pred_dir = np.diff(test_preds) > 0
                    dir_acc = float(np.mean(actual_dir == pred_dir) * 100)
                else:
                    dir_acc = 50.0

                residual_std = float(np.std(actual_test - test_preds))
                test_dates = [d.strftime('%Y-%m-%d') for d in df.index[train_size:train_size + min_len]]
            else:
                rmse, mae, mape, r2, dir_acc = 0.0, 0.0, 0.0, 0.0, 50.0
                residual_std = float(np.std(close_prices[-20:]))
                test_preds = []
                actual_test = []
                test_dates = []

            # Multi-step future forecast
            last_window = scaled_data[-Config.LOOKBACK_WINDOW:].copy()
            future_scaled_preds = []

            for step in range(forecast_days):
                curr_input = last_window[-Config.LOOKBACK_WINDOW:].reshape(1, Config.LOOKBACK_WINDOW, 1)
                next_pred = model.predict(curr_input, verbose=0)
                future_scaled_preds.append(next_pred[0][0])
                last_window = np.append(last_window, next_pred)[1:].reshape(-1, 1)

            future_prices = scaler.inverse_transform(np.array(future_scaled_preds).reshape(-1, 1)).flatten()

            # Generate future business day dates
            last_date = df.index[-1]
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days * 2, freq='B')
            future_dates = [d.strftime('%Y-%m-%d') for d in future_dates[:forecast_days]]

            # Confidence interval band (expanding cone of uncertainty)
            upper_band = []
            lower_band = []
            for i, price in enumerate(future_prices):
                # Uncertainty scales mildly with horizon step
                uncertainty = 1.96 * max(residual_std, price * 0.015) * np.sqrt((i + 1) / 10.0)
                upper_band.append(round(float(price + uncertainty), 2))
                lower_band.append(round(float(max(0.0, price - uncertainty)), 2))

            # Historical data serialization (last 180 trading days for fast web display)
            history_window = min(180, len(df))
            hist_df = df.iloc[-history_window:]
            hist_dates = [d.strftime('%Y-%m-%d') for d in hist_df.index]
            hist_prices = [round(float(p), 2) for p in hist_df['Close'].values]

            # Current price and predicted price metrics
            current_price = round(float(close_prices[-1][0]), 2)
            final_pred_price = round(float(future_prices[-1]), 2)
            expected_change = round(final_pred_price - current_price, 2)
            expected_change_pct = round((expected_change / current_price) * 100, 2) if current_price else 0.0

            return {
                "success": True,
                "ticker": ticker,
                "model_status": model_status,
                "forecast_days": forecast_days,
                "current_price": current_price,
                "final_predicted_price": final_pred_price,
                "expected_change": expected_change,
                "expected_change_pct": expected_change_pct,
                "trend": "BULLISH" if expected_change >= 0 else "BEARISH",
                "metrics": {
                    "rmse": round(rmse, 2),
                    "mae": round(mae, 2),
                    "mape": round(mape, 2),
                    "r2_score": round(max(-1.0, r2), 3),
                    "directional_accuracy": round(dir_acc, 1)
                },
                "chart_data": {
                    "history_dates": hist_dates,
                    "history_prices": hist_prices,
                    "test_dates": test_dates,
                    "test_actual": [round(float(x), 2) for x in actual_test],
                    "test_pred": [round(float(x), 2) for x in test_preds],
                    "future_dates": future_dates,
                    "future_prices": [round(float(x), 2) for x in future_prices],
                    "upper_band": upper_band,
                    "lower_band": lower_band
                }
            }
        except Exception as e:
            print(f"[MLService] Prediction pipeline error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Prevent memory leaks across HTTP requests
            tf.keras.backend.clear_session()

ml_service = MLService()
