import sqlite3
import numpy as np
from ml_config import build_model, preprocess_data, fetch_data_incremental
from load_config import load_config_with_env_vars
import joblib

def train_model():
    config = load_config_with_env_vars('config.json')
    
    # Create table if not exists
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            pair TEXT,
            timestamp INTEGER,
            price REAL,
            volume REAL,
            PRIMARY KEY (pair, timestamp)
        )
    ''')
    conn.commit()
    conn.close()
    
    # Fetch incremental data
    print("Fetching historical data...")
    fetch_data_incremental(config)
    
    # Load data from db
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM market_data ORDER BY timestamp')
    data = cursor.fetchall()
    conn.close()
    
    if len(data) < 20:
        print("Not enough data, need more historical data")
        return
    
    print(f"Loaded {len(data)} data points")
    
    # Preprocess
    features, labels = preprocess_data(data, timesteps=10, config=config)
    
    if len(features) == 0:
        print("No features generated")
        return
    
    print(f"Training on {len(features)} samples")
    
    # Train model
    model = build_model()
    model.fit(features, labels)
    
    # Save
    joblib.dump(model, 'model.pkl')
    print("Model trained and saved to model.pkl")

if __name__ == "__main__":
    train_model()