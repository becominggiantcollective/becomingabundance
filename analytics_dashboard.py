#!/usr/bin/env python3
"""
Analytics Dashboard for Arbitrage Bot
Displays trading performance metrics and statistics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_analytics import trading_analytics
from datetime import datetime

def display_dashboard():
    """Display the analytics dashboard"""
    print("\n" + "="*60)
    print("ARBITRAGE BOT ANALYTICS DASHBOARD")
    print("="*60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get performance summary
    summary = trading_analytics.get_performance_summary()

    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {summary['total_trades']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
    print(f"   Total P&L: ${summary['total_pnl']:.2f}")
    print(f"   Average Trade P&L: ${summary['average_trade_pnl']:.2f}")
    print(f"   Sharpe Ratio: {summary['sharpe_ratio']:.2f}")

    if summary['total_trades'] > 0:
        print(f"   Largest Win: ${summary['largest_win']:.2f}")
        print(f"   Largest Loss: ${summary['largest_loss']:.2f}")

    # Recent performance
    recent = trading_analytics.get_recent_performance(7)
    if 'trades' in recent:
        print(f"\n📈 RECENT PERFORMANCE (7 days):")
        print(f"   Trades: {recent['trades']}")
        print(f"   Win Rate: {recent['win_rate']:.1f}%")
        print(f"   P&L: ${recent['pnl']:.2f}")
        print(f"   Avg Trade P&L: ${recent['avg_trade_pnl']:.2f}")

    # DEX Performance
    dex_perf = summary['dex_performance']
    if dex_perf:
        print(f"\n🏛️  DEX PERFORMANCE:")
        sorted_dexes = sorted(dex_perf.items(), key=lambda x: x[1]['pnl'], reverse=True)
        for dex, stats in sorted_dexes[:5]:
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            print(f"   {dex}: {stats['trades']} trades, {win_rate:.1f}% win rate, ${stats['pnl']:.2f} P&L")

    # Pair Performance
    pair_perf = summary['pair_performance']
    if pair_perf:
        print(f"\n💱 PAIR PERFORMANCE:")
        sorted_pairs = sorted(pair_perf.items(), key=lambda x: x[1]['pnl'], reverse=True)
        for pair, stats in sorted_pairs[:5]:
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            print(f"   {pair}: {stats['trades']} trades, {win_rate:.1f}% win rate, ${stats['pnl']:.2f} P&L")

    # Daily stats for last 7 days
    daily_stats = summary['daily_stats']
    if daily_stats:
        print(f"\n📅 DAILY PERFORMANCE (Last 7 days):")
        recent_dates = sorted(daily_stats.keys(), reverse=True)[:7]
        for date in recent_dates:
            stats = daily_stats[date]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            print(f"   {date}: {stats['trades']} trades, {win_rate:.1f}% win rate, ${stats['pnl']:.2f} P&L")

    print("\n" + "="*60)

def display_detailed_report():
    """Display the full detailed report"""
    report = trading_analytics.generate_report()
    print(report)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--detailed":
        display_detailed_report()
    else:
        display_dashboard()