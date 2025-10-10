"""
Small helper to fetch account balance, nonce and simple gas suggestions
for the Amoy testnet from the project's `config.json` + .env.

Usage: run from project root within the venv:
    .venv\Scripts\python.exe scripts\deploy_checks.py

This script will print:
- RPC endpoint used
- Address derived from WALLET_PRIVATE_KEY
- nonce
- balance (in wei and MATIC)
- recommended maxPriorityFeePerGas and maxFeePerGas based on baseFee

It intentionally does not broadcast anything.
"""
import os
import json
import logging
from decimal import Decimal
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account

# project imports
from load_config import load_config_with_env_vars

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


def main():
    cfg = load_config_with_env_vars('config.json')
    # choose chain by TARGET_CHAIN env var (default: Amoy)
    target = os.getenv('TARGET_CHAIN', 'Amoy')
    chain = None
    for c in cfg.get('chains', []):
        name = (c.get('name') or '').lower()
        if name == target.lower():
            chain = c
            break
    if chain is None:
        # fallback: if target is 'amoy' prefer testnet entries
        for c in cfg.get('chains', []):
            if target.lower() == 'amoy' and c.get('is_testnet'):
                chain = c
                break
    if chain is None:
        LOG.error('No Amoy/testnet chain entry found in config.json')
        return

    # support both 'rpc' and 'rpc_url' keys (some configs use rpc_url)
    # support both 'rpc' and 'rpc_url' keys (some configs use rpc_url)
    rpc = chain.get('rpc') or chain.get('rpc_url') or os.getenv(f'{target.upper()}_RPC_URL') or os.getenv('POLYGON_RPC_URL')
    if not rpc:
        LOG.error('No RPC URL found for Amoy in config.json or env')
        return

    LOG.info(f'Using RPC: {rpc}')
    w3 = Web3(Web3.HTTPProvider(rpc))

    # derive account
    pk = os.getenv('WALLET_PRIVATE_KEY')
    if not pk:
        LOG.error('WALLET_PRIVATE_KEY not set in environment (.env)')
        return
    if pk.startswith('0x'):
        pk = pk[2:]
    acct = Account.from_key(pk)
    addr = acct.address

    LOG.info(f'Derived address: {addr}')

    try:
        # POA chains (like Amoy/Polygon variants) use a different extraData length
        # Inject the geth POA middleware to avoid errors when reading blocks
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        nonce = w3.eth.get_transaction_count(addr)
        balance = w3.eth.get_balance(addr)
        LOG.info(f'Nonce: {nonce}')
        LOG.info(f'Balance: {balance} wei ({Decimal(balance) / Decimal(10**18)} MATIC)')

        # get latest block for baseFee
        latest = w3.eth.get_block('latest')
        base_fee = latest.get('baseFeePerGas') if latest else None
        if base_fee:
            # pick priority fee (1.5 gwei as example) but scale to base_fee
            priority = int(1.5 * 10**9)
            max_fee = int(base_fee * 2 + priority)
            LOG.info(f'Base fee (latest block): {base_fee} wei')
            LOG.info(f'Recommended maxPriorityFeePerGas: {priority} wei')
            LOG.info(f'Recommended maxFeePerGas: {max_fee} wei')
        else:
            LOG.warning('No baseFeePerGas found on chain (legacy network?)')
    except Exception as e:
        LOG.error('Error querying chain: %s', e)


if __name__ == '__main__':
    main()
