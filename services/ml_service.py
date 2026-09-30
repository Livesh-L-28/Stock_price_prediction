import os
import time
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
from config import Config

logger = logging.getLogger("alphapulse.ml")

class TrainingProgressCallback(tf.keras.callbacks.Callback):
    """Tracks epoch loss in real-time for live progress streaming."""
    def __init__(self, ticker: str, tracker_dict: dict, total_epochs: int):
        super().__init__()
        self.ticker = ticker
        self.tracker = tracker_dict
        self.total_epochs = total_epochs

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        loss = round(float(logs.get('loss', 0.0)), 5)
        self.tracker[self.ticker] = {
            "epoch": epoch + 1,
            "total_epochs": self.total_epochs,
            "loss": loss,
            "progress_pct": int(((epoch + 1) / self.total_epochs) * 100),
            "status": "training"
        }

class MLService:
    def __init__(self):
        os.makedirs(Config.MODELS_DIR, exist_ok=True)
        # In-memory progress tracking for real-time streaming
        self.training_status = {}

    def _get_model_path(self, ticker: str) -> str:
        safe_ticker = ticker.replace("^", "INDEX_").replace(".", "_")
        return os.path.join(Config.MODELS_DIR, f"{safe_ticker}.keras")

    def is_model_fresh(self, model_path: str, max_age_days: int = 7) -> bool:
        if not os.path.exists(model_path):
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(model_path))
        return (datetime.now() - mtime) < timedelta(days=max_age_days)

    def extract_multivariate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineers a 5-dimensional feature matrix:
        1. Close: Target price
        2. Volume: Normalized trading volume
        3. RSI_14: Relative Strength Index
        4. MACD: Moving Average Convergence Divergence
        5. Spread: Intraday (High - Low) / Close spread
        """
        df = df.copy()
        close = df['Close'].astype(float)
        high = df['High'].astype(float) if 'High' in df.columns else close
        low = df['Low'].astype(float) if 'Low' in df.columns else close
        volume = df['Volume'].astype(float) if 'Volume' in df.columns else pd.Series(1.0, index=df.index)

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI_14'] = (100 - (100 / (1 + rs))).fillna(50.0)

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = (ema12 - ema26).fillna(0.0)

        # Intraday High-Low Spread %
        df['Spread'] = ((high - low) / (close + 1e-6)).fillna(0.01)

        # Ensure volume is numeric and non-zero
        df['Volume'] = volume.replace(0, np.nan).ffill().bfill().fillna(1.0)

        # Clean and select core 5 features
        feature_cols = ['Close', 'Volume', 'RSI_14', 'MACD', 'Spread']
        return df[feature_cols].dropna()

    def prepare_multivariate_dataset(self, feature_data: np.ndarray, target_data: np.ndarray, time_step: int = 60):
        """Creates sliding 3D sequences: (samples, time_step, n_features)."""
        X, y = [], []
        for i in range(len(feature_data) - time_step):
            X.append(feature_data[i:i + time_step])
            y.append(target_data[i + time_step])
        return np.array(X), np.array(y)

    def build_multivariate_lstm(self, input_shape: tuple = (60, 5)) -> Sequential:
        """Constructs an optimized Multivariate Stacked LSTM architecture."""
        model = Sequential([
            Input(shape=input_shape),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation="relu"),
            Dense(1)
        ])
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mean_squared_error")
        return model

    def train_or_load_model(self, ticker: str, X_train: np.ndarray, y_train: np.ndarray, force_retrain: bool = False):
        """Loads cached model if fresh; otherwise trains and persists a new one."""
        model_path = self._get_model_path(ticker)
        n_features = X_train.shape[2]

        if not force_retrain and self.is_model_fresh(model_path):
            try:
                logger.info(f"Loading cached model for {ticker} from {model_path}")
                model = load_model(model_path)
                # Verify input feature dimension matches
                if model.input_shape[-1] == n_features:
                    return model, "Cached (Sub-Second)"
            except Exception as e:
                logger.warning(f"Could not load cached model for {ticker}: {e}. Retraining...")

        # Train new model
        logger.info(f"Training fresh multivariate LSTM model for {ticker} (Shape: {X_train.shape})")
        self.training_status[ticker] = {
            "epoch": 0,
            "total_epochs": Config.LSTM_EPOCHS,
            "loss": 0.0,
            "progress_pct": 0,
            "status": "starting"
        }

        model = self.build_multivariate_lstm(input_shape=(Config.LOOKBACK_WINDOW, n_features))
        progress_cb = TrainingProgressCallback(ticker, self.training_status, Config.LSTM_EPOCHS)
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=3, restore_best_weights=True)

        model.fit(
            X_train,
            y_train,
            epochs=Config.LSTM_EPOCHS,
            batch_size=Config.LSTM_BATCH_SIZE,
            verbose=0,
            callbacks=[progress_cb, early_stop]
        )

        self.training_status[ticker]["status"] = "completed"

        try:
            model.save(model_path)
            logger.info(f"Successfully saved multivariate model to {model_path}")
        except Exception as e:
            logger.error(f"Could not save model to {model_path}: {e}")

        return model, "Trained Fresh (Multivariate)"

    def run_prediction_pipeline(self, ticker: str, df: pd.DataFrame, forecast_days: int = 30, force_retrain: bool = False) -> dict:
        """
        Complete end-to-end production multivariate prediction pipeline:
        1. Feature engineering (Close, Volume, RSI, MACD, Spread)
        2. Dual MinMaxScaler normalizers (feature matrix + target Close)
        3. Train/Test split for empirical out-of-sample backtesting
        4. Model persistence / Checkpoint loading
        5. Empirical metric calculation (RMSE, MAE, MAPE, R2, Directional Acc)
        6. Hybrid Ensemble multi-step autoregressive forecasting
        7. 95% dynamic statistical confidence cone
        """
        try:
            if df.empty or len(df) < Config.LOOKBACK_WINDOW + 25:
                raise ValueError(f"Need at least {Config.LOOKBACK_WINDOW + 25} historical trading days. Found {len(df)}.")

            forecast_days = max(Config.MIN_FORECAST_DAYS, min(forecast_days, Config.MAX_FORECAST_DAYS))

            # 1. Feature Engineering
            feature_df = self.extract_multivariate_features(df)
            raw_features = feature_df.values.astype(float)
            raw_target = feature_df[['Close']].values.astype(float)

            feature_scaler = MinMaxScaler(feature_range=(0, 1))
            target_scaler = MinMaxScaler(feature_range=(0, 1))

            scaled_features = feature_scaler.fit_transform(raw_features)
            scaled_target = target_scaler.fit_transform(raw_target).flatten()

            # 2. Train / Test Split (Hold out last 40 days for rigorous evaluation)
            test_size = min(40, int(len(scaled_features) * 0.15))
            train_size = len(scaled_features) - test_size

            feat_train = scaled_features[:train_size]
            target_train = scaled_target[:train_size]

            # 3. Prepare sequences
            X_train, y_train = self.prepare_multivariate_dataset(feat_train, target_train, time_step=Config.LOOKBACK_WINDOW)
            if len(X_train) == 0:
                raise ValueError("Insufficient training samples for sequence construction.")

            # 4. Load or Train Model
            model, model_status = self.train_or_load_model(ticker, X_train, y_train, force_retrain=force_retrain)

            # 5. Out-of-Sample Backtesting on Test Split
            test_feat_window = scaled_features[train_size - Config.LOOKBACK_WINDOW:]
            X_test, _ = self.prepare_multivariate_dataset(test_feat_window, scaled_target[train_size - Config.LOOKBACK_WINDOW:], time_step=Config.LOOKBACK_WINDOW)

            if len(X_test) > 0:
                scaled_test_preds = model.predict(X_test, verbose=0)
                test_preds = target_scaler.inverse_transform(scaled_test_preds).flatten()
                actual_test = raw_target[train_size:].flatten()

                min_len = min(len(test_preds), len(actual_test))
                test_preds = test_preds[:min_len]
                actual_test = actual_test[:min_len]

                rmse = float(np.sqrt(mean_squared_error(actual_test, test_preds)))
                mae = float(mean_absolute_error(actual_test, test_preds))
                mape = float(np.mean(np.abs((actual_test - test_preds) / (actual_test + 1e-6))) * 100)
                r2 = float(r2_score(actual_test, test_preds))

                if min_len > 1:
                    actual_dir = np.diff(actual_test) > 0
                    pred_dir = np.diff(test_preds) > 0
                    dir_acc = float(np.mean(actual_dir == pred_dir) * 100)
                else:
                    dir_acc = 50.0

                residual_std = float(np.std(actual_test - test_preds))
                test_dates = [d.strftime('%Y-%m-%d') for d in feature_df.index[train_size:train_size + min_len]]
            else:
                rmse, mae, mape, r2, dir_acc = 0.0, 0.0, 0.0, 0.0, 50.0
                residual_std = float(np.std(raw_target[-20:]))
                test_preds, actual_test, test_dates = [], [], []

            # 6. Multi-Step Autoregressive Hybrid Forecast
            current_window = scaled_features[-Config.LOOKBACK_WINDOW:].copy()
            future_scaled_preds = []

            # Baseline linear trend anchor (prevents unconstrained drift)
            recent_prices = raw_target[-30:].flatten()
            trend_slope = np.polyfit(np.arange(len(recent_prices)), recent_prices, 1)[0]
            current_spot = float(recent_prices[-1])

            # Rolling stats for aux features
            avg_volume_scaled = float(np.mean(current_window[:, 1]))
            avg_spread_scaled = float(np.mean(current_window[:, 4]))

            for step in range(forecast_days):
                input_seq = current_window.reshape(1, Config.LOOKBACK_WINDOW, scaled_features.shape[1])
                pred_scaled = model.predict(input_seq, verbose=0)[0][0]
                future_scaled_preds.append(pred_scaled)

                # Assemble next multivariate feature vector
                # Close = pred_scaled, Volume = mean, RSI = scaled approx, MACD = decay approx, Spread = mean
                last_rsi_scaled = current_window[-1, 2]
                last_macd_scaled = current_window[-1, 3] * 0.95  # mild decay towards mean
                next_row = np.array([pred_scaled, avg_volume_scaled, last_rsi_scaled, last_macd_scaled, avg_spread_scaled])

                # Slide window by 1 step
                current_window = np.vstack([current_window[1:], next_row])

            raw_future_lstm = target_scaler.inverse_transform(np.array(future_scaled_preds).reshape(-1, 1)).flatten()

            # Hybrid Ensemble: 80% LSTM + 20% Grounded Empirical Trend
            future_prices = []
            for h, p_lstm in enumerate(raw_future_lstm):
                trend_anchor = current_spot + (trend_slope * (h + 1))
                # Weighted blend
                blended = (0.80 * p_lstm) + (0.20 * trend_anchor)
                future_prices.append(blended)
            future_prices = np.array(future_prices)

            # Generate future business day calendar
            last_date = feature_df.index[-1]
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days * 2, freq='B')
            future_dates = [d.strftime('%Y-%m-%d') for d in future_dates[:forecast_days]]

            # 7. Dynamic 95% Confidence Interval Cone
            upper_band, lower_band = [], []
            for i, price in enumerate(future_prices):
                step_uncertainty = 1.96 * max(residual_std, price * 0.012) * np.sqrt((i + 1) / 10.0)
                upper_band.append(round(float(price + step_uncertainty), 2))
                lower_band.append(round(float(max(0.0, price - step_uncertainty)), 2))

            # Historical display window (last 180 trading days)
            hist_window = min(180, len(feature_df))
            hist_df = feature_df.iloc[-hist_window:]
            hist_dates = [d.strftime('%Y-%m-%d') for d in hist_df.index]
            hist_prices = [round(float(p), 2) for p in hist_df['Close'].values]

            final_pred_price = round(float(future_prices[-1]), 2)
            expected_change = round(final_pred_price - current_spot, 2)
            expected_change_pct = round((expected_change / current_spot) * 100, 2) if current_spot else 0.0

            return {
                "success": True,
                "ticker": ticker,
                "model_status": model_status,
                "forecast_days": forecast_days,
                "current_price": round(current_spot, 2),
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
            logger.error(f"Multivariate prediction pipeline error for {ticker}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            tf.keras.backend.clear_session()

ml_service = MLService()
