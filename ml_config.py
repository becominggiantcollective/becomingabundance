import numpy as np
import joblib
from xgboost import XGBClassifier
import requests
import sqlite3
from ratelimit import limits, sleep_and_retry
import time

def build_model():
    return XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1)

@sleep_and_retry
@limits(calls=100, period=3600)
def fetch_data_incremental(config):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS market_data (
        pair TEXT,
        price REAL,
        volume REAL,
        timestamp INTEGER
    )''')
    for pair in config['pairs']:
        if pair['name'] == 'USDC/ETH':
            coin = 'ethereum'
        elif pair['name'] == 'USDT/WMATIC':
            coin = 'matic-network'
        else:
            continue
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=30"
        response = requests.get(url)
        if response.status_code != 200:
            continue
        data = response.json()
        prices = data['prices']
        total_volumes = data['total_volumes']
        for i, (ts, price) in enumerate(prices):
            volume = total_volumes[i][1]
            timestamp = int(ts / 1000)  # ms to s
            cursor.execute('INSERT OR IGNORE INTO market_data VALUES (?, ?, ?, ?)', (pair['name'], price, volume, timestamp))
    conn.commit()
    conn.close()

def get_pair_id(token0, token1):
    # Not needed for CoinGecko
    return None

def preprocess_data(prices, volumes, timesteps=10):
    features = []
    for i in range(timesteps, len(prices)):
        window_prices = prices[i-timesteps:i]
        window_volumes = volumes[i-timesteps:i]
        price_diff = prices[i] - window_prices[-1]
        avg_volume = np.mean(window_volumes)
        volatility = np.std(window_prices)
        trend = (window_prices[-1] - window_prices[0]) / window_prices[0] if window_prices[0] != 0 else 0
        # ATR calculation
        tr = [abs(window_prices[j] - window_prices[j-1]) for j in range(1, len(window_prices))]
        atr = np.mean(tr) if tr else 0
        chainlink = 1  # Placeholder
        features.append([price_diff, avg_volume, volatility, trend, atr, chainlink])
    return np.array(features)

def predict_opportunity(features):
    model = joblib.load('model.pkl')
    return model.predict_proba(features.reshape(1, -1))[:, 1][0]