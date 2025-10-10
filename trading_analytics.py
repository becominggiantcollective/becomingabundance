import time
import logging
import json
import statistics
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

class TradingAnalytics:
    """Advanced analytics and performance tracking for arbitrage trading"""

    def __init__(self):
        self.trade_log = []
        self.daily_stats = defaultdict(dict)
        self.weekly_stats = defaultdict(dict)
        self.monthly_stats = defaultdict(dict)

        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        self.average_win = 0.0
        self.average_loss = 0.0

        # DEX performance
        self.dex_performance = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'pnl': 0.0,
            'avg_profit': 0.0
        })

        # Token pair performance
        self.pair_performance = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'pnl': 0.0,
            'avg_profit': 0.0
        })

        # Load saved analytics
        self.load_analytics()

    def load_analytics(self):
        """Load saved analytics from file"""
        try:
            if os.path.exists('trading_analytics.json'):
                with open('trading_analytics.json', 'r') as f:
                    data = json.load(f)
                    self.trade_log = data.get('trade_log', [])
                    self.total_trades = data.get('total_trades', 0)
                    self.winning_trades = data.get('winning_trades', 0)
                    self.total_pnl = data.get('total_pnl', 0.0)
                    logging.info(f"Loaded analytics: {self.total_trades} trades, P&L: ${self.total_pnl:.2f}")
        except Exception as e:
            logging.warning(f"Failed to load analytics: {e}")

    def save_analytics(self):
        """Save analytics to file"""
        try:
            data = {
                'trade_log': self.trade_log[-1000:],  # Keep last 1000 trades
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_pnl': self.total_pnl,
                'win_rate': self.get_win_rate(),
                'avg_trade_pnl': self.get_average_trade_pnl(),
                'sharpe_ratio': self.calculate_sharpe_ratio(),
                'timestamp': time.time()
            }
            with open('trading_analytics.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save analytics: {e}")

    def record_trade(self, trade_data: Dict):
        """Record a completed trade"""
        trade_entry = {
            'timestamp': time.time(),
            'token_in': trade_data.get('tokenIn'),
            'token_out': trade_data.get('tokenOut'),
            'buy_dex': trade_data.get('buy_dex'),
            'sell_dex': trade_data.get('sell_dex'),
            'amount': trade_data.get('amount'),
            'entry_price': trade_data.get('buy_price'),
            'exit_price': trade_data.get('sell_price'),
            'profit_pct': trade_data.get('profit_pct'),
            'profit_usd': trade_data.get('profit_usd', 0),
            'gas_cost_usd': trade_data.get('gas_cost_usd', 0),
            'success': trade_data.get('success', False),
            'net_profit': trade_data.get('net_profit', 0)
        }

        self.trade_log.append(trade_entry)
        self.total_trades += 1

        if trade_entry['success']:
            self.winning_trades += 1
            self.largest_win = max(self.largest_win, trade_entry['net_profit'])
        else:
            self.losing_trades += 1
            self.largest_loss = min(self.largest_loss, trade_entry['net_profit'])

        self.total_pnl += trade_entry['net_profit']

        # Update DEX performance
        dex = trade_entry['sell_dex']  # Primary DEX used
        self.dex_performance[dex]['trades'] += 1
        self.dex_performance[dex]['pnl'] += trade_entry['net_profit']
        if trade_entry['success']:
            self.dex_performance[dex]['wins'] += 1

        # Update pair performance
        pair = f"{trade_entry['token_in'][:6]}_{trade_entry['token_out'][:6]}"
        self.pair_performance[pair]['trades'] += 1
        self.pair_performance[pair]['pnl'] += trade_entry['net_profit']
        if trade_entry['success']:
            self.pair_performance[pair]['wins'] += 1

        # Update daily stats
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = {'trades': 0, 'pnl': 0.0, 'wins': 0}

        self.daily_stats[today]['trades'] += 1
        self.daily_stats[today]['pnl'] += trade_entry['net_profit']
        if trade_entry['success']:
            self.daily_stats[today]['wins'] += 1

        self.save_analytics()
        logging.info(f"Trade recorded: {'WIN' if trade_entry['success'] else 'LOSS'} ${trade_entry['net_profit']:.2f}")

    def get_win_rate(self) -> float:
        """Calculate overall win rate"""
        return (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0

    def get_average_trade_pnl(self) -> float:
        """Calculate average P&L per trade"""
        return self.total_pnl / self.total_trades if self.total_trades > 0 else 0.0

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(self.trade_log) < 2:
            return 0.0

        # Get daily returns
        daily_returns = []
        current_day = None
        day_pnl = 0.0

        for trade in self.trade_log:
            trade_day = datetime.fromtimestamp(trade['timestamp']).date().isoformat()
            if current_day and trade_day != current_day:
                if day_pnl != 0:
                    daily_returns.append(day_pnl)
                day_pnl = 0.0
            current_day = trade_day
            day_pnl += trade['net_profit']

        if day_pnl != 0:
            daily_returns.append(day_pnl)

        if len(daily_returns) < 2:
            return 0.0

        try:
            avg_return = statistics.mean(daily_returns)
            std_return = statistics.stdev(daily_returns)
            return (avg_return - risk_free_rate) / std_return if std_return > 0 else 0.0
        except:
            return 0.0

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.get_win_rate(),
            'total_pnl': self.total_pnl,
            'average_trade_pnl': self.get_average_trade_pnl(),
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'dex_performance': dict(self.dex_performance),
            'pair_performance': dict(self.pair_performance),
            'daily_stats': dict(self.daily_stats)
        }

    def get_recent_performance(self, days: int = 7) -> Dict:
        """Get performance for recent days"""
        cutoff_time = time.time() - (days * 86400)
        recent_trades = [t for t in self.trade_log if t['timestamp'] > cutoff_time]

        if not recent_trades:
            return {'message': f'No trades in last {days} days'}

        wins = sum(1 for t in recent_trades if t['success'])
        pnl = sum(t['net_profit'] for t in recent_trades)

        return {
            'period_days': days,
            'trades': len(recent_trades),
            'wins': wins,
            'win_rate': (wins / len(recent_trades) * 100) if recent_trades else 0,
            'pnl': pnl,
            'avg_trade_pnl': pnl / len(recent_trades) if recent_trades else 0
        }

    def generate_report(self) -> str:
        """Generate a human-readable performance report"""
        summary = self.get_performance_summary()
        recent = self.get_recent_performance(7)

        report = f"""
=== ARBITRAGE BOT PERFORMANCE REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL PERFORMANCE:
- Total Trades: {summary['total_trades']}
- Win Rate: {summary['win_rate']:.1f}%
- Total P&L: ${summary['total_pnl']:.2f}
- Average Trade P&L: ${summary['average_trade_pnl']:.2f}
- Sharpe Ratio: {summary['sharpe_ratio']:.2f}

RECENT PERFORMANCE (7 days):
- Trades: {recent.get('trades', 0)}
- Win Rate: {recent.get('win_rate', 0):.1f}%
- P&L: ${recent.get('pnl', 0):.2f}

TOP PERFORMING DEXes:
"""

        # Sort DEXes by P&L
        sorted_dexes = sorted(summary['dex_performance'].items(),
                            key=lambda x: x[1]['pnl'], reverse=True)

        for dex, stats in sorted_dexes[:5]:
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            report += f"- {dex}: {stats['trades']} trades, {win_rate:.1f}% win rate, ${stats['pnl']:.2f} P&L\n"

        report += "\nTOP PERFORMING PAIRS:\n"

        # Sort pairs by P&L
        sorted_pairs = sorted(summary['pair_performance'].items(),
                            key=lambda x: x[1]['pnl'], reverse=True)

        for pair, stats in sorted_pairs[:5]:
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            report += f"- {pair}: {stats['trades']} trades, {win_rate:.1f}% win rate, ${stats['pnl']:.2f} P&L\n"

        return report

# Global analytics instance
trading_analytics = TradingAnalytics()