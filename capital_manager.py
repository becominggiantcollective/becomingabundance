import time
import logging
import json
import os
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class Position:
    token_in: str
    token_out: str
    amount: int
    entry_price: float
    timestamp: int
    status: str  # 'open', 'closed', 'failed'

@dataclass
class TradeResult:
    profit_usd: float
    gas_cost_usd: float
    success: bool
    timestamp: int
    details: Dict

class CapitalManager:
    """Manages capital allocation and position sizing for arbitrage trading"""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.locked_capital = 0.0
        self.total_pnl = 0.0

        # Position sizing
        self.max_position_pct = 0.1  # Max 10% of capital per trade
        self.min_position_usd = 10.0
        self.max_position_usd = 100.0

        # Risk limits
        self.max_daily_loss_pct = 0.05  # 5% max daily loss
        self.daily_loss_limit = initial_capital * self.max_daily_loss_pct
        self.daily_pnl = 0.0
        self.daily_start_time = time.time()

        # Track positions and trades
        self.open_positions: Dict[str, Position] = {}
        self.trade_history: List[TradeResult] = []
        self.consecutive_losses = 0

        # Load saved state
        self.load_state()

    def load_state(self):
        """Load saved capital state from file"""
        try:
            if os.path.exists('capital_state.json'):
                with open('capital_state.json', 'r') as f:
                    state = json.load(f)
                    self.available_capital = state.get('available_capital', self.initial_capital)
                    self.total_pnl = state.get('total_pnl', 0.0)
                    self.daily_pnl = state.get('daily_pnl', 0.0)
                    self.consecutive_losses = state.get('consecutive_losses', 0)
                    logging.info(f"Loaded capital state: ${self.available_capital:.2f} available")
        except Exception as e:
            logging.warning(f"Failed to load capital state: {e}")

    def save_state(self):
        """Save capital state to file"""
        try:
            state = {
                'available_capital': self.available_capital,
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
                'consecutive_losses': self.consecutive_losses,
                'timestamp': time.time()
            }
            with open('capital_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save capital state: {e}")

    def reset_daily_stats(self):
        """Reset daily statistics"""
        current_time = time.time()
        if current_time - self.daily_start_time > 86400:  # 24 hours
            self.daily_pnl = 0.0
            self.daily_start_time = current_time
            logging.info("Daily capital statistics reset")

    def calculate_position_size(self, opportunity: Dict) -> float:
        """Calculate appropriate position size for a trade"""
        self.reset_daily_stats()

        # Base position size on available capital
        max_position = min(
            self.available_capital * self.max_position_pct,
            self.max_position_usd
        )

        # Adjust based on opportunity confidence
        profit_pct = opportunity.get('profit_pct', 0)
        confidence_multiplier = min(1.0, profit_pct / 3.0)  # Scale with profit potential

        position_size = max_position * confidence_multiplier
        position_size = max(self.min_position_usd, min(position_size, self.max_position_usd))

        # Check if we have enough capital
        if position_size > self.available_capital * 0.95:  # Leave 5% buffer
            position_size = self.available_capital * 0.95

        return position_size

    def can_open_position(self, position_size: float) -> bool:
        """Check if we can open a position of given size"""
        # Check daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            logging.warning(".2f")
            return False

        # Check available capital
        if position_size > self.available_capital:
            logging.warning(".2f")
            return False

        # Check consecutive losses
        if self.consecutive_losses >= 3:
            logging.warning(f"Too many consecutive losses ({self.consecutive_losses}), stopping trading")
            return False

        return True

    def open_position(self, opportunity: Dict, position_size: float) -> Optional[str]:
        """Open a new trading position"""
        if not self.can_open_position(position_size):
            return None

        position_id = f"{opportunity['tokenIn'][:6]}_{opportunity['tokenOut'][:6]}_{int(time.time())}"

        position = Position(
            token_in=opportunity['tokenIn'],
            token_out=opportunity['tokenOut'],
            amount=int(position_size * 10**6),  # Convert to wei (assuming 6 decimals)
            entry_price=opportunity['buy_price'],
            timestamp=int(time.time()),
            status='open'
        )

        self.open_positions[position_id] = position
        self.available_capital -= position_size
        self.locked_capital += position_size

        self.save_state()
        logging.info(f"Opened position {position_id}: ${position_size:.2f} ({opportunity['buy_dex']} -> {opportunity['sell_dex']})")
        return position_id

    def close_position(self, position_id: str, exit_price: float, gas_cost_usd: float, success: bool):
        """Close a trading position and record P&L"""
        if position_id not in self.open_positions:
            logging.error(f"Position {position_id} not found")
            return

        position = self.open_positions[position_id]

        # Calculate P&L
        if success:
            # Simplified P&L calculation
            profit_usd = (position.amount / 10**6) * (exit_price - position.entry_price) * 0.01  # Rough estimate
            profit_usd -= gas_cost_usd
        else:
            profit_usd = -gas_cost_usd  # Just gas cost on failure

        # Update capital
        self.available_capital += (position.amount / 10**6) + profit_usd
        self.locked_capital -= (position.amount / 10**6)
        self.total_pnl += profit_usd
        self.daily_pnl += profit_usd

        # Update consecutive losses
        if success:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # Record trade result
        trade_result = TradeResult(
            profit_usd=profit_usd,
            gas_cost_usd=gas_cost_usd,
            success=success,
            timestamp=int(time.time()),
            details={
                'position_id': position_id,
                'entry_price': position.entry_price,
                'exit_price': exit_price,
                'amount': position.amount
            }
        )
        self.trade_history.append(trade_result)

        # Remove position
        position.status = 'closed' if success else 'failed'
        del self.open_positions[position_id]

        self.save_state()
        logging.info(f"Closed position {position_id}: {'PROFIT' if success else 'LOSS'} ${profit_usd:.2f}")

    def get_status(self) -> Dict:
        """Get current capital status"""
        return {
            'total_capital': self.available_capital + self.locked_capital,
            'available_capital': self.available_capital,
            'locked_capital': self.locked_capital,
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'win_rate': self.calculate_win_rate(),
            'open_positions': len(self.open_positions),
            'consecutive_losses': self.consecutive_losses
        }

    def calculate_win_rate(self) -> float:
        """Calculate win rate from trade history"""
        if not self.trade_history:
            return 0.0

        wins = sum(1 for trade in self.trade_history if trade.success)
        return (wins / len(self.trade_history)) * 100

    def emergency_stop(self):
        """Emergency stop - close all positions at market"""
        logging.error("EMERGENCY STOP ACTIVATED - Closing all positions")

        for position_id in list(self.open_positions.keys()):
            # Close at current price (simplified)
            self.close_position(position_id, self.open_positions[position_id].entry_price, 0, False)

# Global capital manager instance
capital_manager = CapitalManager()