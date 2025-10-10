"""
Post-deploy checks: attach to deployed contract and call read-only getters.
Usage: .venv\Scripts\python.exe scripts\post_deploy_checks.py
"""
import os
import json
import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware
from load_config import load_config_with_env_vars
from deploy import compile_with_solc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


def load_compiled_abi(solc_version='0.8.0'):
    compiled = compile_with_solc(solc_version)
    return compiled['abi']


def main():
    cfg = load_config_with_env_vars('config.json')
    chain = None
    for c in cfg.get('chains', []):
        if c.get('name') == 'Amoy':
            chain = c
            break
    if not chain:
        LOG.error('Amoy not found in config.json')
        return
    rpc = chain.get('rpc_url') or chain.get('rpc')
    if not rpc:
        LOG.error('No RPC for Amoy')
        return
    w3 = Web3(Web3.HTTPProvider(rpc))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    addr = cfg.get('contract_address')
    if not addr:
        LOG.error('contract_address missing in config.json')
        return

    abi = load_compiled_abi('0.8.0')
    contract = w3.eth.contract(address=Web3.toChecksumAddress(addr), abi=abi)

    try:
        owner = contract.functions.owner().call()
        min_profit = contract.functions.minProfit().call()
        LOG.info(f'Owner: {owner}')
        LOG.info(f'minProfit: {min_profit}')
    except Exception as e:
        LOG.error('Error calling contract: %s', e)


if __name__ == '__main__':
    main()
