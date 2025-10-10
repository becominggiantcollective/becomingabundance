import time
import logging
from typing import Dict, Optional
from decimal import Decimal
from web3 import Web3

class GasOptimizer:
    """Optimizes gas usage for arbitrage trading"""

    def __init__(self):
        self.gas_history = []
        self.optimal_gas_window = 300  # 5 minutes
        self.max_gas_price_gwei = 500  # Maximum gas price we're willing to pay
        self.min_gas_price_gwei = 30   # Minimum gas price for fast execution

        # Gas price tiers for different urgency levels
        self.gas_tiers = {
            'slow': 1.0,      # 1x current gas price
            'standard': 1.2,  # 1.2x current gas price
            'fast': 1.5,      # 1.5x current gas price
            'urgent': 2.0     # 2x current gas price for immediate execution
        }

    def get_optimal_gas_price(self, w3: Web3, urgency: str = 'standard') -> int:
        """Get optimal gas price based on current market conditions and urgency"""
        try:
            current_gas = w3.eth.gas_price
            current_gwei = Web3.fromWei(current_gas, 'gwei')

            # Store gas history for trend analysis
            self.gas_history.append({
                'price': current_gwei,
                'timestamp': time.time()
            })

            # Keep only recent history
            cutoff_time = time.time() - self.optimal_gas_window
            self.gas_history = [g for g in self.gas_history if g['timestamp'] > cutoff_time]

            # Calculate optimal price based on urgency
            multiplier = Decimal(str(self.gas_tiers.get(urgency, 1.2)))
            optimal_gwei = current_gwei * multiplier

            # Apply bounds
            optimal_gwei = max(self.min_gas_price_gwei, min(optimal_gwei, self.max_gas_price_gwei))

            optimal_wei = Web3.toWei(optimal_gwei, 'gwei')

            logging.debug(f"Gas optimization - Current: {current_gwei:.1f} gwei, "
                         f"Optimal ({urgency}): {optimal_gwei:.1f} gwei")

            return optimal_wei

        except Exception as e:
            logging.warning(f"Failed to optimize gas price: {e}")
            return w3.eth.gas_price

    def should_execute_trade(self, gas_price: int, w3: Web3, profit_usd: float) -> bool:
        """Determine if gas price makes trade profitable"""
        gas_cost_usd = self.calculate_gas_cost_usd(gas_price, w3)

        # Trade is profitable if profit > gas cost * 1.5 (leave some margin)
        min_profit_ratio = 1.5
        is_profitable = profit_usd > (gas_cost_usd * min_profit_ratio)

        if not is_profitable:
            logging.debug(f"Trade not profitable - Profit: ${profit_usd:.2f}, "
                         f"Gas cost: ${gas_cost_usd:.2f}, Ratio: {profit_usd/gas_cost_usd:.2f}")

        return is_profitable

    def calculate_gas_cost_usd(self, gas_price: int, w3: Web3, gas_limit: int = 300000) -> float:
        """Calculate gas cost in USD (Polygon uses MATIC for gas)"""
        try:
            # Estimate gas cost (300k gas for flash loan arbitrage)
            gas_cost_wei = gas_price * gas_limit

            # Convert to MATIC (Polygon native token)
            gas_cost_matic = Web3.fromWei(gas_cost_wei, 'ether')

            # Get MATIC price dynamically from oracle
            from price_oracle import price_oracle
            matic_price_usd = price_oracle.get_matic_price_usd()

            gas_cost_usd = float(gas_cost_matic) * matic_price_usd

            return gas_cost_usd

        except Exception as e:
            logging.warning(f"Failed to calculate gas cost: {e}")
            return 0.15  # Fallback estimate for Polygon gas

    def get_gas_trend(self) -> str:
        """Analyze gas price trend"""
        if len(self.gas_history) < 5:
            return "insufficient_data"

        recent_prices = [g['price'] for g in self.gas_history[-5:]]
        avg_recent = sum(recent_prices) / len(recent_prices)

        older_prices = [g['price'] for g in self.gas_history[-10:-5]] if len(self.gas_history) >= 10 else recent_prices
        avg_older = sum(older_prices) / len(older_prices)

        if avg_recent > avg_older * Decimal('1.1'):
            return "rising"
        elif avg_recent < avg_older * Decimal('0.9'):
            return "falling"
        else:
            return "stable"

    def get_optimal_execution_time(self, w3: Web3) -> Optional[int]:
        """Suggest optimal execution time based on gas trends"""
        trend = self.get_gas_trend()

        if trend == "falling":
            return int(time.time())  # Execute now
        elif trend == "rising":
            return int(time.time() + 300)  # Wait 5 minutes
        else:
            return int(time.time())  # Execute now

# Global gas optimizer instance
gas_optimizer = GasOptimizer()