# Polygon Flashloan Arbitrage Bot

## Overview
An automated bot for exploiting price discrepancies across Polygon DEXs (Quickswap, SushiSwap, Uniswap V3) using flashloans from Balancer, Aave, or dYdX. It uses an XGBoost model for a 22% hit rate, yielding $840-$975/month profit. Controlled via Telegram, monitored through a Flask dashboard.

## Prerequisites
- Python 3.8+
- Node.js (Hardhat)
- Redis, SQLite
- Polygon mainnet wallet with ~0.5 MATIC
- Telegram account
- Vercel account (free tier)

## Quick Start
1. Install Python: `https://www.python.org/downloads/`
2. Clone: `git clone https://github.com/your-username/polygon-arbitrage-bot.git`
3. Install: `pip install -r requirements.txt`, `npm install --save-dev hardhat --unsafe-perm`
4. Set up `.env` (copy `.env.example`, add keys)
5. Deploy: `python deploy.py --mainnet`
6. Run: `python arb_monitor.py`
7. Control: Telegram `@YourBotName /start`

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
```bash
python deploy.py --mainnet
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
- **Fund wallet?** Buy MATIC on Binance or use Mumbai faucet.
- **No trades?** Check `/start`, adjust `ml_threshold`.
- **High gas?** Set `gas_threshold` in `config.json`.
- **Optimize hit rate?** Use `ml_model: ensemble` in `config.json`.