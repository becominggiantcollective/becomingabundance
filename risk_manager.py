import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class TradeRisk:
    profit_pct: float
    gas_cost_usd: float
    slippage_risk: float
    liquidity_risk: float
    overall_risk: RiskLevel

class RiskManager:
    """Advanced risk management for arbitrage trading"""

    def __init__(self):
        self.daily_loss_limit = 50  # USD
        self.max_consecutive_losses = 3
        self.min_profit_threshold = 2.0  # 2% minimum profit
        self.max_position_size = 1000  # USD max per trade

        # Track performance
        self.daily_pnl = 0
        self.consecutive_losses = 0
        self.last_reset = time.time()
        self.emergency_stop = False

        # Gas price thresholds (gwei)
        self.gas_thresholds = {
            RiskLevel.LOW: 50,
            RiskLevel.MEDIUM: 100,
            RiskLevel.HIGH: 200,
            RiskLevel.EXTREME: 500
        }

    def reset_daily_stats(self):
        """Reset daily statistics"""
        current_time = time.time()
        if current_time - self.last_reset > 86400:  # 24 hours
            self.daily_pnl = 0
            self.consecutive_losses = 0
            self.last_reset = current_time
            self.emergency_stop = False
            logging.info("Daily statistics reset")

    def calculate_gas_cost_usd(self, gas_price_wei: int, estimated_gas: int = 300000) -> float:
        """Calculate gas cost in USD"""
        # Rough conversion: 1 ETH = ~$2000, gas price in wei
        eth_cost = (gas_price_wei * estimated_gas) / 10**18
        return eth_cost * 2000  # Convert to USD

    def assess_trade_risk(self, opportunity: Dict, gas_price: int) -> TradeRisk:
        """Assess overall risk of a trade opportunity"""
        profit_pct = opportunity['profit_pct']
        gas_cost_usd = self.calculate_gas_cost_usd(gas_price)

        # Calculate net profit after gas costs
        # Assume trade size creates enough profit to cover gas
        estimated_trade_value = 1000  # USD (rough estimate)
        gas_cost_pct = (gas_cost_usd / estimated_trade_value) * 100
        net_profit_pct = profit_pct - gas_cost_pct

        # Slippage risk based on liquidity (simplified)
        volume = 1000000  # From opportunity
        slippage_risk = min(5.0, 1000000 / max(volume, 1000))  # Higher volume = lower risk

        # Liquidity risk
        liquidity_risk = 2.0 if volume < 10000 else 1.0 if volume < 100000 else 0.5

        # Overall risk assessment
        if net_profit_pct > 3.0 and slippage_risk < 1.0:
            overall_risk = RiskLevel.LOW
        elif net_profit_pct > 2.0 and slippage_risk < 2.0:
            overall_risk = RiskLevel.MEDIUM
        elif net_profit_pct > 1.0:
            overall_risk = RiskLevel.HIGH
        else:
            overall_risk = RiskLevel.EXTREME

        return TradeRisk(
            profit_pct=net_profit_pct,
            gas_cost_usd=gas_cost_usd,
            slippage_risk=slippage_risk,
            liquidity_risk=liquidity_risk,
            overall_risk=overall_risk
        )

    def should_execute_trade(self, opportunity: Dict, gas_price: int) -> Tuple[bool, str]:
        """Determine if a trade should be executed based on risk assessment"""
        self.reset_daily_stats()

        if self.emergency_stop:
            return False, "Emergency stop activated"

        # Check daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            self.emergency_stop = True
            return False, f"Daily loss limit exceeded: ${abs(self.daily_pnl)}"

        # Assess trade risk
        risk = self.assess_trade_risk(opportunity, gas_price)

        # Minimum profit threshold
        if risk.profit_pct < self.min_profit_threshold:
            return False, ".2f"

        # Gas price check
        gas_gwei = gas_price / 10**9
        if gas_gwei > self.gas_thresholds[RiskLevel.HIGH]:
            return False, ".1f"

        # Risk level check
        if risk.overall_risk == RiskLevel.EXTREME:
            return False, f"Risk too high: {risk.overall_risk.value}"

        # Position size check
        trade_value = min(self.max_position_size, 1000)  # USD
        if trade_value > self.max_position_size:
            return False, ".0f"

        return True, ".2f"

    def record_trade_result(self, profit_usd: float, success: bool):
        """Record the result of a trade"""
        self.daily_pnl += profit_usd

        if success:
            self.consecutive_losses = 0
            logging.info(".2f")
        else:
            self.consecutive_losses += 1
            logging.warning(".2f")

            if self.consecutive_losses >= self.max_consecutive_losses:
                self.emergency_stop = True
                logging.error(f"Emergency stop activated after {self.consecutive_losses} consecutive losses")

    def get_status(self) -> Dict:
        """Get current risk management status"""
        return {
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'emergency_stop': self.emergency_stop,
            'daily_loss_limit': self.daily_loss_limit,
            'max_consecutive_losses': self.max_consecutive_losses
        }

# Global risk manager instance
risk_manager = RiskManager()