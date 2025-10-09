import numpy as np
import joblib
from xgboost import XGBClassifier
import requests
import sqlite3
from ratelimit import limits, sleep_and_retry

def build_model():
    return XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1)

@sleep_and_retry
@limits(calls=100, period=3600)
def fetch_data_incremental(config):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    latest = time.time() - 3 * 24 * 3600
    for pair in config['pairs']:
        cursor.execute('SELECT * FROM market_data WHERE pair = ? AND timestamp > ?', (pair['name'], latest))
        data = cursor.fetchall()
        if not data:
            url = f"https://api.thegraph.com/subgraphs/name/quickswap/{pair['name']}"
            response = requests.post(url, json={'query': '{ pairDayDatas(first: 100) { price, volume } }'})
            data = response.json()['data']['pairDayDatas']
            cursor.executemany('INSERT INTO market_data VALUES (?, ?, ?)', [(pair['name'], d['price'], time.time()) for d in data])
            conn.commit()
    return data

def fetch_chainlink_data(pair):
    contract = w3.eth.contract(address='0xChainlinkPriceFeed', abi=chainlink_abi)
    return contract.functions.latestPrice().call()

def preprocess_data(data, timesteps=10):
    features = []
    for i in range(timesteps, len(data)):
        window = data[i-timesteps:i]
        volatility = np.std([d['price'] for d in window])
        if volatility > config['max_volatility']:
            continue
        features.append([d['price'] - window[-1]['price'], d['volume'], fetch_chainlink_data(config['pairs'][0]['name'])])
    return np.array(features)

def predict_opportunity(features):
    model = joblib.load('model.pkl')
    return model.predict_proba(features)[:, 1]