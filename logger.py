import sqlite3
import csv
import gzip
import shutil
from pysqlcipher3 import dbapi2 as sqlcipher
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def init_db():
    conn = sqlcipher.connect('bot.db')
    conn.execute('PRAGMA key = ?', (os.getenv('DB_KEY'),))
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS trades (timestamp REAL, pair TEXT, profit REAL, prediction_score REAL, tx_hash TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback (timestamp REAL, message TEXT)')
    cursor.execute('CREATE VIEW recent_trades AS SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20')
    cursor.execute('CREATE INDEX idx_pair ON trades(pair)')
    conn.commit()

def robust_redis(redis_client, op, retries=5):
    for _ in range(retries):
        try:
            return op()
        except redis.RedisError:
            time.sleep(0.5)
    raise Exception("Redis failed")

def log_trade(tx_hash, pair, profit, address):
    conn = sqlcipher.connect('bot.db')
    conn.execute('PRAGMA key = ?', (os.getenv('DB_KEY'),))
    cursor = conn.cursor()
    masked_address = address[:6] + '...' + address[-4:]
    cursor.execute('INSERT INTO trades (timestamp, pair, profit, tx_hash) VALUES (?, ?, ?, ?)', (time.time(), pair, profit, masked_address))
    conn.commit()
    robust_redis(redis_client, lambda: redis_client.publish('trades', json.dumps({'tx_hash': tx_hash, 'pair': pair, 'profit': profit})))

def export_audit_report(filename='audit.csv'):
    conn = sqlcipher.connect('bot.db')
    conn.execute('PRAGMA key = ?', (os.getenv('DB_KEY'),))
    cursor = conn.cursor()
    cursor.execute('SELECT strftime("%Y-%m-%dT%H:%M:%SZ", timestamp), pair, profit, fees, tx_hash FROM trades')
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['Timestamp', 'Pair', 'Profit', 'Fees', 'Tx Hash'])
        writer.writerows(cursor.fetchall())

def backup_db():
    with open('bot.db', 'rb') as f_in:
        with gzip.open(f'backup_{datetime.now().strftime("%Y%m%d")}.db.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)