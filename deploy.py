

import time
import redis
import os
import argparse
import logging
import json
from web3 import Web3
import requests
from load_config import load_config_with_env_vars
from dotenv import load_dotenv
from web3.middleware import geth_poa_middleware

# Optional: compile with py-solc-x
try:
    from solcx import install_solc, compile_standard
    SOLCX_AVAILABLE = True
except Exception:
    SOLCX_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

def get_gas_price():
    cache = redis_client.get('gas_price')
    if cache and time.time() - float(redis_client.get('gas_price_time') or 0) < 30:
        return float(cache)
    response = requests.get('https://gasstation-mainnet.matic.network/v2')
    price = response.json()['fast']['maxFee']
    redis_client.setex('gas_price', 30, price)
    redis_client.set('gas_price_time', time.time())
    return price

def robust_deploy(w3, tx):
    try:
        return w3.eth.send_transaction(tx)
    except Exception as e:
        raise Exception(f"Deployment failed: {e}")

def deploy_contract(compiled, network='mainnet', dry_run=False):
    config = load_config_with_env_vars('config.json')
    # Choose chain by name when possible. Prefer 'Amoy' as the testnet (user's Amoy testnet)
    target_chain_name = 'Polygon' if network == 'mainnet' else 'Amoy'
    chain = None
    for c in config.get('chains', []):
        if c.get('name') == target_chain_name:
            chain = c
            break
    if chain is None:
        # try to use env var for Mumbai RPC
        mumbai_rpc = os.getenv('MUMBAI_RPC_URL') or os.getenv('POLYGON_MUMBAI_RPC')
        if network != 'mainnet' and mumbai_rpc:
            logger.warning('Mumbai entry not found in config.json; using MUMBAI_RPC_URL from environment')
            chain = {'name': 'Mumbai', 'chain_id': 80001, 'rpc_url': mumbai_rpc}
        else:
            # fallback to first chain
            logger.warning('Target chain not found in config.json; falling back to first chain entry')
            chain = config['chains'][0]
    logger.info(f'Connecting to RPC: {chain.get("rpc_url")}')
    w3 = Web3(Web3.HTTPProvider(chain['rpc_url']))
    # Inject POA middleware for chains like Polygon/Mumbai
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        logger.info('Injected geth_poa_middleware')
    except Exception:
        logger.debug('Could not inject POA middleware')
    account = w3.eth.account.from_key(os.getenv('WALLET_PRIVATE_KEY'))
    contract = w3.eth.contract(abi=compiled['abi'], bytecode=compiled['bytecode'])
    # Extract router addresses from dex definitions and convert to checksum addresses
    dexes_cfg = config.get('dexes', [])
    dexes = []
    for d in dexes_cfg:
        if isinstance(d, dict):
            addr = d.get('router') or d.get('address')
            if addr:
                try:
                    dexes.append(Web3.toChecksumAddress(addr))
                except Exception:
                    dexes.append(addr)
        elif isinstance(d, str):
            try:
                dexes.append(Web3.toChecksumAddress(d))
            except Exception:
                dexes.append(d)

    loan_providers_cfg = config.get('loanProviders', [])
    loan_providers = []
    for lp in loan_providers_cfg:
        if isinstance(lp, dict):
            addr = lp.get('address') or lp.get('router')
            if addr:
                try:
                    loan_providers.append(Web3.toChecksumAddress(addr))
                except Exception:
                    loan_providers.append(addr)
        elif isinstance(lp, str):
            try:
                loan_providers.append(Web3.toChecksumAddress(lp))
            except Exception:
                loan_providers.append(lp)

    min_profit = int(config.get('minProfit', 0) or 0)
    logger.info(f'Using dex router addresses: {dexes}, loan_providers: {loan_providers}, min_profit: {min_profit}')

    constructor_args = (dexes, loan_providers, min_profit)
    try:
        unsigned_tx = contract.constructor(*constructor_args).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            # will set gas and gasPrice below
        })
    except Exception as e:
        logger.error('Constructor encoding failed')
        logger.error(f'constructor_args: {constructor_args}')
        # show types
        try:
            arg_types = [type(a) for a in constructor_args]
            logger.error(f'constructor_arg_types: {arg_types}')
            # for iterables, show inner types
            for i, a in enumerate(constructor_args):
                if hasattr(a, '__iter__') and not isinstance(a, (str, bytes)):
                    logger.error(f'arg[{i}] length: {len(list(a))}')
                    logger.error(f'arg[{i}] sample: {list(a)[:5]}')
        except Exception:
            pass
        raise

    # Estimate gas
    try:
        estimated = w3.eth.estimate_gas({
            'from': unsigned_tx['from'],
            'to': unsigned_tx.get('to', ''),
            'data': unsigned_tx['data']
        })
        unsigned_tx['gas'] = int(estimated * 1.2)
    except Exception:
        unsigned_tx['gas'] = 2000000
    # Allow overrides for nonce and EIP-1559 fees via environment variables
    override_nonce = os.getenv('OVERRIDE_NONCE')
    override_max_prio = os.getenv('OVERRIDE_MAX_PRIORITY_FEE')
    override_max_fee = os.getenv('OVERRIDE_MAX_FEE')

    if override_nonce is not None:
        try:
            unsigned_tx['nonce'] = int(override_nonce)
        except Exception:
            logger.warning('Invalid OVERRIDE_NONCE value; using node nonce')

    # If maxFee/maxPriority overrides provided, use EIP-1559 fields
    if override_max_fee or override_max_prio:
        if override_max_fee:
            try:
                unsigned_tx['maxFeePerGas'] = int(override_max_fee)
            except Exception:
                logger.warning('Invalid OVERRIDE_MAX_FEE; ignoring')
        if override_max_prio:
            try:
                unsigned_tx['maxPriorityFeePerGas'] = int(override_max_prio)
            except Exception:
                logger.warning('Invalid OVERRIDE_MAX_PRIORITY_FEE; ignoring')
        # remove legacy gasPrice if present
        if 'gasPrice' in unsigned_tx:
            unsigned_tx.pop('gasPrice')
    else:
        # Gas price (legacy) as fallback
        try:
            gp = get_gas_price()
            unsigned_tx['gasPrice'] = Web3.toWei(gp, 'gwei')
        except Exception:
            unsigned_tx['gasPrice'] = Web3.toWei(100, 'gwei')

    # Set chainId if available
    if 'chain_id' in chain:
        unsigned_tx['chainId'] = chain['chain_id']

    # If dry_run, just output the unsigned transaction for inspection
    if dry_run:
        logger.info('Dry-run mode: transaction built but not sent')
        print(json.dumps(unsigned_tx, indent=2, default=str))
        # persist the unsigned transaction so it can be signed/sent separately
        try:
            with open('.last_unsigned_tx.json', 'w', encoding='utf-8') as f:
                json.dump(unsigned_tx, f, indent=2, default=str)
            logger.info('Wrote unsigned transaction to .last_unsigned_tx.json')
        except Exception:
            logger.exception('Failed to write .last_unsigned_tx.json')
        return None

    # Sign and send
    try:
        signed = account.sign_transaction(unsigned_tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f'Deployed contract at: {receipt.contractAddress}')
    except Exception as e:
        raise Exception(f'Deployment failed: {e}')
    # Optionally verify contract if verify_contract is defined
    # Optionally verify contract if verify_contract is defined
    try:
        verify_contract(receipt.contractAddress, open('ArbitrageBot.sol').read())
    except Exception:
        # ignore verification errors
        pass
    return receipt.contractAddress
# Ensure redis_client is defined
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


def compile_with_solc(solc_version='0.8.0'):
    if not SOLCX_AVAILABLE:
        raise RuntimeError('py-solc-x is not installed. Run: pip install py-solc-x')
    install_solc(solc_version)
    with open('ArbitrageBot.sol', 'r', encoding='utf-8') as f:
        source = f.read()
    # Try to include OpenZeppelin imports by fetching their source files from GitHub
    oz_version = 'v4.9.3'
    # Try multiple CDNs for resilience
    oz_targets = {
        '@openzeppelin/contracts/security/ReentrancyGuard.sol': [
            f'https://cdn.jsdelivr.net/gh/OpenZeppelin/openzeppelin-contracts@{oz_version}/contracts/security/ReentrancyGuard.sol',
            f'https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/{oz_version}/contracts/security/ReentrancyGuard.sol',
            f'https://unpkg.com/@openzeppelin/contracts@{oz_version}/security/ReentrancyGuard.sol'
        ],
        '@openzeppelin/contracts/access/Ownable.sol': [
            f'https://cdn.jsdelivr.net/gh/OpenZeppelin/openzeppelin-contracts@{oz_version}/contracts/access/Ownable.sol',
            f'https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/{oz_version}/contracts/access/Ownable.sol',
            f'https://unpkg.com/@openzeppelin/contracts@{oz_version}/access/Ownable.sol'
        ],
        '@openzeppelin/contracts/utils/Context.sol': [
            f'https://cdn.jsdelivr.net/gh/OpenZeppelin/openzeppelin-contracts@{oz_version}/contracts/utils/Context.sol',
            f'https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/{oz_version}/contracts/utils/Context.sol',
            f'https://unpkg.com/@openzeppelin/contracts@{oz_version}/utils/Context.sol'
        ]
    }
    sources = {'ArbitrageBot.sol': {'content': source}}
    for path, urls in oz_targets.items():
        content = None
        # try each CDN/url with several retries and exponential backoff
        for url in urls:
            backoff = 0.5
            for attempt in range(5):
                try:
                    resp = requests.get(url, timeout=15)
                    resp.raise_for_status()
                    content = resp.text
                    break
                except Exception as e:
                    logger.debug(f'Attempt {attempt+1} failed for {url}: {e}')
                    time.sleep(backoff)
                    backoff *= 1.8
            if content:
                break
        if content:
            sources[path] = {'content': content}
        else:
            logger.warning(f'Could not fetch OpenZeppelin file for {path}. Compilation may fail.')

    # Build standard input for solc
    standard_input = {
        'language': 'Solidity',
        'sources': sources,
        'settings': {'outputSelection': {'*': {'*': ['abi', 'evm.bytecode.object']}}}
    }
    compiled = compile_standard(standard_input, solc_version=solc_version)
    contract_key = list(compiled['contracts']['ArbitrageBot.sol'].keys())[0]
    abi = compiled['contracts']['ArbitrageBot.sol'][contract_key]['abi']
    bytecode = compiled['contracts']['ArbitrageBot.sol'][contract_key]['evm']['bytecode']['object']
    return {'abi': abi, 'bytecode': bytecode}


def main():
    parser = argparse.ArgumentParser(description='Compile and deploy ArbitrageBot')
    parser.add_argument('--network', choices=['mainnet', 'testnet'], default='testnet')
    parser.add_argument('--solc', default='0.8.0', help='Solidity compiler version')
    parser.add_argument('--dry-run', action='store_true', help='Build transaction but do not broadcast')
    args = parser.parse_args()

    network = args.network
    logger.info(f'Starting deploy on {network}')
    # Compile
    try:
        compiled = compile_with_solc(args.solc)
        logger.info('Compilation successful')
    except Exception as e:
        logger.error(f'Compilation failed: {e}')
        return

    # Deploy
    try:
        address = deploy_contract(compiled, network='mainnet' if network == 'mainnet' else 'testnet', dry_run=args.dry_run)
        if address:
            logger.info(f'Contract deployed at {address}')
            print(address)
    except Exception as e:
        logger.error(f'Deployment error: {e}')


if __name__ == '__main__':
    main()