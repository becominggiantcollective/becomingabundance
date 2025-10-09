import pytest
from web3 import Web3
from ml_config import predict_opportunity

def test_contract_deployment():
    w3 = Web3(Web3.HTTPProvider('https://rpc-mumbai.maticvigil.com'))
    assert deploy_contract(compiled, 'testnet') is not None

def test_ml_prediction():
    features = fetch_data_incremental(config)
    assert predict_opportunity(features) >= 0

def test_redis_connection():
    assert redis_client.ping()

def test_sqlite_logging():
    cursor.execute('INSERT INTO trades (timestamp, pair, profit) VALUES (?, ?, ?)', (time.time(), 'USDC/ETH', 0.65))
    conn.commit()
    cursor.execute('SELECT * FROM trades')
    assert len(cursor.fetchall()) > 0