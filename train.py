import sqlite3
import numpy as np
import joblib
from ml_config import fetch_data_incremental, preprocess_data, build_model
from load_config import load_config_with_env_vars

config = load_config_with_env_vars('config.json')

# Collect data
print("Collecting data...")
fetch_data_incremental(config)

# Get data from db
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

all_features = []
all_labels = []

for pair in config['pairs']:
    cursor.execute('SELECT price, volume FROM market_data WHERE pair = ? ORDER BY timestamp', (pair['name'],))
    rows = cursor.fetchall()
    prices = [row[0] for row in rows]
    volumes = [row[1] for row in rows]
    print(f"Data for {pair['name']}: {len(prices)} points")
    if len(prices) < 20:  # Need enough data
        continue
    features = preprocess_data(prices, volumes, timesteps=10)
    for i in range(len(features)):
        window_start = i
        window_end = i + 10
        window_prices = prices[window_start:window_end]
        window_volumes = volumes[window_start:window_end]
        current_price = prices[window_end]
        avg = np.mean(window_prices)
        std = np.std(window_prices)
        z_score = (current_price - avg) / std if std > 0 else 0
        current_volume = volumes[window_end] if window_end < len(volumes) else volumes[-1]
        avg_vol_7day = np.mean(window_volumes[-7:]) if len(window_volumes) >= 7 else np.mean(window_volumes)
        label = 1 if z_score < -2 else 0  # High confidence: 2 std below mean
        all_features.append(features[i])
        all_labels.append(label)

conn.close()

print(f"Total features: {len(all_features)}, Labels: {sum(all_labels)} are 1 out of {len(all_labels)}")

if all_features:
    print(f"Training on {len(all_features)} samples...")
    model = build_model()
    model.fit(np.array(all_features), np.array(all_labels))
    joblib.dump(model, 'model.pkl')
    print("Model trained and saved to model.pkl")
else:
    print("Not enough data to train model")