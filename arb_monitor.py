
import time
import json
import redis
import os
import logging
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from ml_config import predict_opportunity
from load_config import load_config_with_env_vars
from dotenv import load_dotenv
from price_oracle import fetch_data
from risk_manager import risk_manager
from capital_manager import capital_manager
from trading_analytics import trading_analytics

# Set up logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

test_mode = True  # Set to True for testing without execution

UNISWAP_V2_FACTORY_ABI = [
    {
        "constant": True,
        "inputs": [
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

UNISWAP_V2_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def robust_call(call, retries=10, delay=1.0):
    for attempt in range(retries):
        try:
            return call()
        except Exception as e:
            logging.warning(f"RPC call failed (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    logging.error("RPC failed after all retries")
    raise Exception("RPC failed")

def find_arbitrage_opportunities(w3, config, gas_price):
    """Find arbitrage opportunities by comparing prices across DEXes"""
    opportunities = []
    
    # Group pairs by token pair (ignoring DEX)
    pair_groups = {}
    for pair in config['pairs']:
        token_pair = (pair['tokenIn'], pair['tokenOut'])
        if token_pair not in pair_groups:
            pair_groups[token_pair] = []
        pair_groups[token_pair].append(pair)
    
    # For each token pair, compare prices across DEXes
    for token_pair, pairs in pair_groups.items():
        if len(pairs) < 2:
            continue  # Need at least 2 DEXes to compare
            
        prices = {}
        for pair in pairs:
            features = fetch_data(pair, w3, config)
            if features[0] > 0:  # Valid price
                prices[pair['dex']] = {
                    'price': features[0],
                    'pair': pair,
                    'router': next((d['router'] for d in config['dexes'] if d['name'] == pair['dex']), None)
                }
        
        if len(prices) < 2:
            continue
            
        # Find best buy and sell prices
        best_buy_dex = min(prices.keys(), key=lambda x: prices[x]['price'])
        best_sell_dex = max(prices.keys(), key=lambda x: prices[x]['price'])
        
        buy_price = prices[best_buy_dex]['price']
        sell_price = prices[best_sell_dex]['price']
        
        # Calculate arbitrage profit percentage
        if buy_price > 0:
            profit_pct = (sell_price - buy_price) / buy_price * 100
            
            # Use risk manager for trade assessment
            opportunity = {
                'tokenIn': token_pair[0],
                'tokenOut': token_pair[1],
                'buy_dex': best_buy_dex,
                'sell_dex': best_sell_dex,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit_pct': profit_pct,
                'buy_router': prices[best_buy_dex]['router'],
                'sell_router': prices[best_sell_dex]['router'],
                'amount': 1000000
            }
            
            # Check if trade should be executed
            should_trade, reason = risk_manager.should_execute_trade(opportunity, gas_price)
            
            if should_trade:
                opportunities.append(opportunity)
            else:
                logging.debug(f"Trade rejected: {reason}")
    
    return opportunities

def monitor():
    load_dotenv()  # Ensure .env is loaded
    logging.info("Loading config...")
    config = load_config_with_env_vars('config.json')
    logging.info("Config loaded")
    # Use Polygon chain
    chain = config['chains'][0]  # Polygon
    rpc_urls = chain['rpc_url']
    if isinstance(rpc_urls, list):
        w3 = None
        for url in rpc_urls:
            try:
                temp_w3 = Web3(Web3.HTTPProvider(url))
                temp_w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                # Test with gas_price
                temp_w3.eth.gas_price
                w3 = temp_w3
                logging.info(f"Connected to RPC: {url}")
                break
            except Exception as e:
                logging.warning(f"Failed to connect to {url}: {e}")
                continue
        if not w3:
            raise Exception("No working RPC URL found")
    else:
        w3 = Web3(Web3.HTTPProvider(rpc_urls))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        try:
            w3.eth.gas_price
        except Exception as e:
            raise Exception(f"Failed to connect to RPC: {rpc_urls} - {e}")
    logging.info("Web3 setup done")
    
    # Set up account
    pk = os.getenv('WALLET_PRIVATE_KEY')
    if not pk:
        logging.error("WALLET_PRIVATE_KEY not set")
        raise Exception("WALLET_PRIVATE_KEY not set")
    if pk.startswith('0x'):
        pk = pk[2:]
    account = Account.from_key(pk)
    w3.eth.default_account = account.address
    logging.info("Account setup done")
    
    contract_address = config.get('contract_address')
    if not contract_address:
        logging.error("contract_address not set in config")
        raise Exception("contract_address not set in config")
    contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=config.get('contract_abi', []))
    logging.info("Contract setup done")
    
    loan_provider = config['loanProviders'][0]['address']  # Use first loan provider
    
    last_report_time = time.time()
    report_interval = 3600  # Generate report every hour
    
    while True:
        current_time = time.time()
        
        # Generate periodic analytics report
        if current_time - last_report_time > report_interval:
            report = trading_analytics.generate_report()
            logging.info(f"\n{report}")
            last_report_time = current_time
        
        logging.info("Monitoring for arbitrage opportunities...")
        gas_price = robust_call(lambda: w3.eth.gas_price)
        if gas_price > w3.to_wei(config['gas_threshold'], 'gwei'):
            logging.info("Gas too high, skipping")
            time.sleep(config['poll_interval'])
            continue
        
        # Find real arbitrage opportunities
        opportunities = find_arbitrage_opportunities(w3, config, gas_price)
        
        for opp in opportunities:
            logging.info(f"Found arbitrage opportunity: {opp['tokenIn'][:10]}... -> {opp['tokenOut'][:10]}... "
                        f"Profit: {opp['profit_pct']:.2f}% Buy: {opp['buy_dex']} Sell: {opp['sell_dex']}")
            
            # Calculate position size using capital manager
            position_size_usd = capital_manager.calculate_position_size(opp)
            
            if not capital_manager.can_open_position(position_size_usd):
                logging.warning(f"Cannot open position: insufficient capital or risk limits")
                continue
            
            # Convert USD position size to token amount (simplified)
            amount_wei = int(position_size_usd * 10**6)  # Assume 6 decimals for stablecoins
            
            # Update opportunity with calculated amount
            opp['amount'] = amount_wei
            
            # Build path for arbitrage: buy on one DEX, sell on another
            path = [w3.to_checksum_address(opp['tokenIn']), w3.to_checksum_address(opp['tokenOut'])]
            
            # For cross-DEX arbitrage, we need to execute on the sell DEX (higher price)
            dex_router = w3.to_checksum_address(opp['sell_router'])
            
            # Build transaction
            tx = contract.functions.executeArbitrage(
                w3.to_checksum_address(opp['tokenIn']),
                w3.to_checksum_address(opp['tokenOut']),
                opp['amount'],
                path,
                dex_router,
                w3.to_checksum_address(loan_provider)
            ).build_transaction({
                'from': account.address,
                'nonce': w3.eth.get_transaction_count(account.address),
                'gas': 300000,  # Higher gas limit for flash loan
                'gasPrice': gas_price,
                'chainId': chain['chain_id']
            })
            
            # Sign and send
            signed_tx = account.sign_transaction(tx)
            if test_mode:
                logging.info(f"TEST MODE: Would execute arbitrage - Buy {opp['buy_price']:.6f} on {opp['buy_dex']}, "
                           f"Sell {opp['sell_price']:.6f} on {opp['sell_dex']}, Profit: {opp['profit_pct']:.2f}%, "
                           f"Position: ${position_size_usd:.2f}")
            else:
                try:
                    tx_hash = robust_call(lambda: w3.eth.send_raw_transaction(signed_tx.raw_transaction))
                    logging.info(f"Arbitrage executed: {tx_hash.hex()}")
                    
                    # Open position in capital manager
                    position_id = capital_manager.open_position(opp, position_size_usd)
                    
                    # In production, we'd monitor the transaction and close position when confirmed
                    # For now, assume success and close immediately (simplified)
                    gas_cost_usd = risk_manager.calculate_gas_cost_usd(gas_price)
                    capital_manager.close_position(position_id, opp['sell_price'], gas_cost_usd, True)
                    
                    # Record successful trade in analytics
                    trade_data = {
                        'tokenIn': opp['tokenIn'],
                        'tokenOut': opp['tokenOut'],
                        'buy_dex': opp['buy_dex'],
                        'sell_dex': opp['sell_dex'],
                        'amount': opp['amount'],
                        'buy_price': opp['buy_price'],
                        'sell_price': opp['sell_price'],
                        'profit_pct': opp['profit_pct'],
                        'profit_usd': position_size_usd * (opp['profit_pct'] / 100),
                        'gas_cost_usd': gas_cost_usd,
                        'success': True,
                        'net_profit': position_size_usd * (opp['profit_pct'] / 100) - gas_cost_usd
                    }
                    trading_analytics.record_trade(trade_data)
                    
                except Exception as e:
                    logging.error(f"Failed to execute arbitrage: {e}")
                    
                    # Record failed trade
                    gas_cost_usd = risk_manager.calculate_gas_cost_usd(gas_price)
                    risk_manager.record_trade_result(-gas_cost_usd, False)
                    
                    # Record failed trade in analytics
                    trade_data = {
                        'tokenIn': opp['tokenIn'],
                        'tokenOut': opp['tokenOut'],
                        'buy_dex': opp['buy_dex'],
                        'sell_dex': opp['sell_dex'],
                        'amount': opp['amount'],
                        'buy_price': opp['buy_price'],
                        'sell_price': opp['sell_price'],
                        'profit_pct': opp['profit_pct'],
                        'profit_usd': 0,
                        'gas_cost_usd': gas_cost_usd,
                        'success': False,
                        'net_profit': -gas_cost_usd
                    }
                    trading_analytics.record_trade(trade_data)
        
        time.sleep(config['poll_interval'])

if __name__ == "__main__":
    try:
        monitor()
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        raise