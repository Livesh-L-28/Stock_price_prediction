<div align="center">

# 📈 Deep Learning Stock Price Predictor

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/TensorFlow-2.20-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white" alt="TensorFlow" />
  <img src="https://img.shields.io/badge/Keras-3.10-D00000?style=for-the-badge&logo=keras&logoColor=white" alt="Keras" />
  <img src="https://img.shields.io/badge/Pandas-2.3-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
  <img src="https://img.shields.io/badge/scikit--learn-1.6-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="scikit-learn" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License" />
</p>

### 🚀 Real-time Indian 🇮🇳 & US 🇺🇸 Stock Trend Prediction Powered by Stacked LSTM Neural Networks

---

</div>

## 🌟 Key Features

- **🧠 Stacked LSTM Neural Network**: Predicts future stock price trends based on a 60-day historical window.
- **🇮🇳 Top 50 Indian Stocks (NSE/BSE)**: Pre-configured with blue-chip Indian stocks (`RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`, `ICICIBANK.NS`, etc.).
- **🇺🇸 Top 50 US Stocks (NYSE/NASDAQ)**: Pre-configured with US market leaders (`AAPL`, `MSFT`, `GOOGL`, `NVDA`, `AMZN`, `TSLA`, etc.).
- **⚡ Automated Caching & Auto-Update**: Real-time market data retrieval via Yahoo Finance (`yfinance`) with intelligent local caching.
- **📊 Dynamic Visualizations**: Generates inline actual vs. predicted price visualization plots embedded as Base64 images.
- **🎨 Sleek Dark-Themed UI**: Modern web dashboard built with Flask and Bootstrap 5.

---

## 🛠️ Technology Stack

| Domain | Technologies |
| :--- | :--- |
| **Backend Framework** | ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white) Python Web Server |
| **Machine Learning** | ![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white) ![Keras](https://img.shields.io/badge/Keras-D00000?style=flat-square&logo=keras&logoColor=white) Stacked LSTM (50 units x 2 + Dropout + Dense layers) |
| **Data Processing** | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white) ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white) `MinMaxScaler` |
| **Data Provider** | ![yfinance](https://img.shields.io/badge/Yahoo--Finance-6001D2?style=flat-square&logo=yahoo&logoColor=white) `yfinance` 3-Year Historical API |
| **Visualization** | ![Matplotlib](https://img.shields.io/badge/Matplotlib-11557c?style=flat-square) Matplotlib Agg non-GUI backend |
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap--5-7952B3?style=flat-square&logo=bootstrap&logoColor=white) Dark Mode |

---

## 🧠 Model Architecture & Pipeline

```mermaid
flowchart TD
    A[📊 Yahoo Finance API] -->|3-Year Historical Data| B(📂 Local CSV Caching)
    B -->|Pre-process & Clean| C[⚙️ MinMaxScaler Normalization]
    C -->|Create 60-Day Sliding Window| D[📦 X_train / Y_train Datasets]
    D --> E[🧠 Stacked LSTM Neural Network]
    
    subgraph LSTM Model Architecture
        E1[LSTM Layer 1 - 50 Units] --> E2[Dropout 20%]
        E2 --> E3[LSTM Layer 2 - 50 Units]
        E3 --> E4[Dropout 20%]
        E4 --> E5[Dense Layer - 25 Units]
        E5 --> E6[Dense Layer - 1 Output Unit]
    end

    E --> LSTM Model Architecture
    LSTM Model Architecture --> F[🔮 Auto-Regressive N-Day Forecast]
    F --> G[📈 Matplotlib Graph Generation]
    G --> H[🌐 Flask Web Dashboard Render]
```

---

## 📂 Project Directory Structure

```
stock_price_predict/
├── 📄 app.py                  # Main Flask application & LSTM model pipeline
├── 📄 README.md                # Project documentation
├── 📄 .gitignore               # Git ignore rules for venv, cache, and OS files
├── 📁 templates/               # HTML Views
│   ├── 📄 index.html           # Market selection landing page (Indian vs US)
│   ├── 📄 indian.html          # Indian stock prediction interface
│   ├── 📄 us.html              # US stock prediction interface
│   └── 📄 predict.html         # Prediction result page & Matplotlib graph display
└── 📁 data/                    # Cached stock CSV files (generated automatically)
    └── 📄 .gitkeep
```

---

## ⚡ Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Livesh28/Stock_price_prediction.git
cd Stock_price_prediction
```

### 2. Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

### 3. Install Dependencies
```bash
pip install flask yfinance pandas numpy matplotlib scikit-learn tensorflow tqdm
```

### 4. Run the Application
```bash
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 💻 How to Use

1. **Select Market**: On the home page, choose between **🇮🇳 Indian Stocks** or **🇺🇸 US Stocks**.
2. **Select Stock Ticker**: Pick a stock symbol from the dropdown or type a custom ticker (e.g. `RELIANCE`, `TCS`, `AAPL`, `NVDA`).
3. **Set Prediction Horizon**: Enter the number of future days to predict (e.g. `30` days).
4. **Predict**: Click **Predict Stock Price**. The application will train the LSTM neural network on recent market history and display:
   - **Target Stock Symbol**
   - **Estimated Final Predicted Price**
   - **Interactive Actual vs. Predicted Price Chart**

---

## 🤝 Contributing

Contributions are welcome! Feel free to submit a Pull Request or open an issue to suggest improvements or new features.

---

## 📜 License

This project is open-source and available under the **MIT License**.
