# Polygon Flashloan Arbitrage Bot

## ⚠️ PROJECT STATUS: EXPERIMENTAL - NOT READY FOR LIVE TRADING ⚠️

**IMPORTANT: This bot is currently in development and NOT profitable. Do not deploy to mainnet or risk real capital.**

---

## 📋 Start Here

If you're just arriving, read these documents in order:

1. **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - Start here for the complete story
2. **[PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md)** - Detailed technical analysis
3. **[STATUS.md](STATUS.md)** - Visual dashboard of current state
4. **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - All 21 bugs and issues
5. **[ROADMAP.md](ROADMAP.md)** - Path to profitability (if you proceed)

**TL;DR:** Bot is in test mode, has critical bugs, uses fake price data, and has never executed a real trade. Would require 150-240 hours + $3k-$8k investment to have a 10-20% chance of profitability.

---

## Overview
An experimental automated bot for exploiting price discrepancies across Polygon DEXs (Quickswap, SushiSwap, Uniswap V3) using flashloans from Balancer or Aave. Currently in **TEST MODE** - no real trades are being executed.

**Current Status:**
- 🔴 Smart contract has critical vulnerabilities and is non-functional
- 🟡 Test mode only - simulations, not real trades
- 🟡 Price oracle uses mock data with artificial spreads
- 🔴 No proven profitability with real market data

**See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for complete project review.**

## Prerequisites
- Python 3.8+
- Node.js (Hardhat)
- Redis, SQLite
- Polygon mainnet wallet with ~0.5 MATIC
- Telegram account
- Vercel account (free tier)

## Quick Start (TEST MODE ONLY)
1. Install Python: `https://www.python.org/downloads/`
2. Clone: `git clone https://github.com/your-username/polygon-arbitrage-bot.git`
3. Install: `pip install -r requirements.txt`, `npm install --save-dev hardhat --unsafe-perm`
4. Set up `.env` (copy `.env.example`, add keys)
5. **DO NOT deploy to mainnet** - contract has critical issues
6. Run in test mode: `python arb_monitor.py` (simulates trades only)
7. Control: Telegram `@YourBotName /start`

**WARNING:** The smart contract is not functional. Deploying to mainnet will result in failed transactions and wasted gas fees.

## Setup
1. Clone repo
2. Install dependencies
3. Set up `.env`:
   - `WALLET_PRIVATE_KEY`: Mainnet wallet
   - `TELEGRAM_TOKEN`: From @BotFather
   - `POLYGONSCAN_API_KEY`
   - `DB_KEY`: For encrypted logs
4. Configure `config.json` (see `config_template.json`)
5. Start Redis: `redis-server`
6. Initialize SQLite: `python logger.py --init-db`

## Deployment
⚠️ **DO NOT DEPLOY TO MAINNET** - Smart contract has critical issues

The contract in `ArbitrageBot.sol` has several blockers:
- Incomplete flash loan repayment logic
- Missing token approvals
- No access controls on callback functions
- Incompatible with Aave V3 and Balancer V2 interfaces

See `PROJECT_ASSESSMENT.md` for full details.

For testing only (Amoy testnet):
```bash
python deploy.py --network testnet --dry-run  # Review transaction first
```

## Usage
- **Telegram**: `/start`, `/stop`, `/status`, `/history`, `/summary`, `/feedback`
- **Dashboard**: `<vercel-url>/dashboard` (stats, charts, feedback)

## Compliance
- **Taxes**: Export logs with `python logger.py --export-csv`
- **KYC/AML**: Optional via Civic for public use

## Community
Join: `<discord-link>`  
Feedback: `/feedback` or `/feedback` on dashboard  
[![Build Status](https://github.com/your-username/polygon-arbitrage-bot/workflows/CI/badge.svg)](https://github.com/your-username/polygon-arbitrage-bot)

## FAQ
- **Is this bot profitable?** No, not currently. See `PROJECT_ASSESSMENT.md` for detailed analysis.
- **Can I make money with this?** Not without significant fixes and development (4-8 weeks minimum).
- **Why is test_mode enabled?** To prevent loss of real capital while the bot is non-functional.
- **What needs to be fixed?** See the "Path to Profitability" section in `PROJECT_ASSESSMENT.md`.
- **Fund wallet?** DO NOT fund a mainnet wallet for this bot yet. Use testnet faucets only.
- **No trades?** Correct - the bot is in test mode and only simulates opportunities.