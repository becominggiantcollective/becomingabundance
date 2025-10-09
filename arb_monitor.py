import time
import json
import redis
from web3 import Web3
from web3.exceptions import Web3Exception
from ml_config import predict_opportunity

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def robust_call(call, retries=5, delay=0.5):
    for _ in range(retries):
        try:
            return call()
        except Web3Exception:
            time.sleep(delay)
    raise Exception("RPC failed")

def monitor(config):
    w3 = Web3(Web3.HTTPProvider(config['chains'][0]['rpc_url']))
    contract = w3.eth.contract(address=config['contract_address'], abi=config['contract_abi'])
    while True:
        if w3.eth.gas_price > w3.to_wei(config['gas_threshold'], 'gwei'):
            w3 = Web3(Web3.HTTPProvider(config['chains'][1]['rpc_url']))  # Arbitrum
            redis_client.set('active_chain', 'Arbitrum')
        for pair in config['pairs']:
            features = fetch_data(pair)
            if predict_opportunity(features) > config['ml_threshold']:
                tx = contract.functions.executeArbitrage(pair['tokenIn'], pair['tokenOut'], pair['amount'], pair['path'], pair['dex'], pair['loanProvider']).build_transaction({
                    'from': w3.eth.default_account,
                    'gasPrice': robust_call(w3.eth.gas_price)
                })
                robust_call(lambda: w3.eth.send_transaction(tx))
        time.sleep(config['poll_interval'])