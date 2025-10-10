import sqlite3
import csv
import gzip
import shutil
import os
import json
import time
from datetime import datetime

import redis

def get_redis_client():
    try:
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_timeout=1,  # Short timeout for faster error detection
            decode_responses=True  # Automatically decode responses to strings
        )
        client.ping()  # Test the connection
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis connection error: {e}")
        return None

redis_client = get_redis_client()
REDIS_AVAILABLE = redis_client is not None

def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS trades (timestamp REAL, pair TEXT, profit REAL, prediction_score REAL, tx_hash TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (timestamp REAL, message TEXT)')
    cursor.execute('CREATE VIEW IF NOT EXISTS recent_trades AS SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pair ON trades(pair)')
    conn.commit()
    return conn

def robust_redis(redis_client, op, retries=5):
    if not REDIS_AVAILABLE:
        return None
    for _ in range(retries):
        try:
            return op()
        except redis.RedisError:
            time.sleep(0.5)
    print("Redis operation failed, continuing without it")
    return None

def log_trade(tx_hash, pair, profit, address):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    masked_address = address[:6] + '...' + address[-4:]
    cursor.execute('INSERT INTO trades (timestamp, pair, profit, tx_hash) VALUES (?, ?, ?, ?)', (time.time(), pair, profit, masked_address))
    conn.commit()
    conn.close()
    robust_redis(redis_client, lambda: redis_client.publish('trades', json.dumps({'tx_hash': tx_hash, 'pair': pair, 'profit': profit})))

def export_audit_report(filename='audit.csv'):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT strftime("%Y-%m-%dT%H:%M:%SZ", datetime(timestamp, "unixepoch")), pair, profit, tx_hash FROM trades')
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['Timestamp', 'Pair', 'Profit', 'Fees', 'Tx Hash'])
        writer.writerows(cursor.fetchall())

def backup_db():
    with open('bot.db', 'rb') as f_in:
        with gzip.open(f'backup_{datetime.now().strftime("%Y%m%d")}.db.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)