# Contributing to Polygon Flashloan Arbitrage Bot

Thank you for contributing! Follow these guidelines to ensure smooth collaboration.

## How to Contribute
- **Issues**: Report bugs/features at `<repo-url>/issues`.
- **Pull Requests**: Fork, branch (`feature/your-feature`), run `python -m pytest test_suite.py`, submit PR.
- **Code Style**: PEP 8 for Python, Solidity style guide.
- **Testing**: Ensure tests pass.

## Bounty Program
- **Sentiment Analysis**: Add X post analysis (+2% hit rate). Bounty: $200.
- **New DEX**: Add Curve to `ArbitrageBot.sol`, `config.json`. Bounty: $150.
- **ML Optimization**: Hit rate >25% (ensemble models). Bounty: $300.
- **New Chain**: Add Base to `config.json`, `deploy.py`. Bounty: $250.
- Payout in MATIC via multisig within 7 days post-merge.

## Development Setup
1. Clone: `git clone <repo-url>`
2. Install: `pip install -r requirements.txt`, `npm install --save-dev hardhat`
3. Configure: Copy `.env.example` to `.env`.
4. Test: `python -m pytest test_suite.py`

## Community
Join: `<discord-link>`  
Feedback: `/feedback` on Telegram or dashboard.