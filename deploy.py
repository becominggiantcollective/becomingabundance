import os
import json
from web3 import Web3
import requests

def get_gas_price():
    cache = redis_client.get('gas_price')
    if cache and time.time() - float(redis_client.get('gas_price_time')) < 30:
        return float(cache)
    response = requests.get('https://gasstation-mainnet.matic.network/v2')
    price = response.json()['fast']['maxFee']
    redis_client.setex('gas_price', 30, price)
    redis_client.set('gas_price_time', time.time())
    return price

def robust_deploy(tx):
    try:
        return w3.eth.send_transaction(tx)
    except:
        raise Exception("Deployment failed")

def deploy_contract(compiled, network='mainnet'):
    chain = config['chains'][0 if network == 'testnet' else 1]
    w3 = Web3(Web3.HTTPProvider(chain['rpc_url']))
    account = w3.eth.account.from_key(os.getenv('WALLET_PRIVATE_KEY'))
    contract = w3.eth.contract(abi=compiled['abi'], bytecode=compiled['bytecode'])
    tx = contract.constructor(config['dexes'], config['loanProviders'], config['minProfit']).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': w3.to_wei(get_gas_price(), 'gwei')
    })
    receipt = robust_deploy(tx)
    verify_contract(receipt.contractAddress, open('ArbitrageBot.sol').read())
    return receipt.contractAddress