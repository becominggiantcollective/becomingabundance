# Known Issues and Bugs

This document lists all identified issues in the trading bot codebase, organized by severity.

## 🔴 Critical Issues (Blockers for Any Real Trading)

### CRITICAL-1: Smart Contract Flash Loan Implementation Missing
**File:** `ArbitrageBot.sol`, lines 33-38  
**Severity:** CRITICAL  
**Status:** 🔴 NOT FIXED

**Issue:**
```solidity
function flashLoanCallback(address token, uint256 amount, bytes memory data) external {
    // ... swap logic ...
    // Repay flash loan (simplified)  <-- NOT IMPLEMENTED
}
```

The flash loan is never repaid. This will cause all flash loan transactions to revert.

**Impact:**
- Contract cannot execute any real arbitrage trades
- All transactions will fail and waste gas
- Flash loan providers will reject the contract

**Fix Required:**
```solidity
// Calculate premium
uint256 premium = (amount * 9) / 10000;  // 0.09% for Aave
uint256 repayAmount = amount + premium;

// Transfer repayment to flash loan provider
IERC20(token).transfer(msg.sender, repayAmount);
```

---

### CRITICAL-2: Flash Loan Callback Interface Mismatch
**File:** `ArbitrageBot.sol`, line 33  
**Severity:** CRITICAL  
**Status:** 🔴 NOT FIXED

**Issue:**
The contract uses `flashLoanCallback()` but flash loan providers use different callback names:
- Aave V3: `executeOperation()`
- Balancer V2: `receiveFlashLoan()`

**Impact:**
Flash loan providers will never call this contract's callback function.

**Fix Required:**
Implement the correct interfaces for each provider. See ROADMAP.md Phase 1.1.A.

---

### CRITICAL-3: Missing Token Approvals
**File:** `ArbitrageBot.sol`, line 35  
**Severity:** CRITICAL  
**Status:** 🔴 NOT FIXED

**Issue:**
DEX routers need approval to spend tokens, but the contract never calls `approve()`.

**Impact:**
All swap transactions will revert with "insufficient allowance" error.

**Fix Required:**
```solidity
IERC20(tokenIn).approve(dexRouter, amountIn);
```

---

### CRITICAL-4: No Access Control on Callback
**File:** `ArbitrageBot.sol`, line 33  
**Severity:** CRITICAL (Security Vulnerability)  
**Status:** 🔴 NOT FIXED

**Issue:**
Any address can call `flashLoanCallback()` with arbitrary data.

**Impact:**
Attacker could drain contract funds by:
1. Calling callback directly
2. Providing malicious data
3. Stealing any tokens in contract

**Fix Required:**
```solidity
mapping(address => bool) public authorizedLenders;

modifier onlyAuthorizedLender() {
    require(authorizedLenders[msg.sender], "Unauthorized");
    _;
}

function flashLoanCallback(...) external onlyAuthorizedLender {
    // ...
}
```

---

### CRITICAL-5: Artificial Price Data
**File:** `price_oracle.py`, lines 98-105  
**Severity:** CRITICAL  
**Status:** 🔴 NOT FIXED

**Issue:**
```python
spreads = {
    'Quickswap': -0.003,  # FAKE spread
    'SushiSwap': 0.005,   # FAKE spread
}
return base_price * (1 + spread)
```

The bot creates artificial arbitrage opportunities instead of finding real ones.

**Impact:**
- All "opportunities" detected are fake
- Real deployment would find no profitable trades
- User would lose money on gas with no profits

**Fix Required:**
Implement real price fetching from DEX reserves. See ROADMAP.md Phase 1.2.

---

## 🟡 High Priority Issues

### HIGH-1: Empty Trading Paths
**File:** `config.json`, all pair entries  
**Severity:** HIGH  
**Status:** 🔴 NOT FIXED

**Issue:**
All trading pairs have `"path": []` which would cause DEX swaps to fail.

**Example:**
```json
{
  "name": "USDC/WMATIC",
  "tokenIn": "0x3c499...",
  "tokenOut": "0x0d500...",
  "path": [],  // <-- EMPTY!
  "dex": "Quickswap"
}
```

**Impact:**
DEX routers require a path array. Empty path = failed transaction.

**Fix Required:**
```json
"path": [
  "0x3c499C542cEF5E3811e1192CE70d8cc03d5C3359",  // tokenIn
  "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"   // tokenOut
]
```

---

### HIGH-2: Invalid Token Addresses
**File:** `config.json`, multiple entries  
**Severity:** HIGH  
**Status:** 🔴 NOT FIXED

**Issues Found:**
1. Line 136: AAVE address has extra 'c' at end:
   ```json
   "tokenIn": "0xD6DF932A45C0f255f85145f286eA0b292B21C90Bc"
   ```
   Should be: `"0xD6DF932A45C0f255f85145f286eA0b292B21C90B"` (40 hex chars)

2. Line 248: MKR address has extra '9' at end:
   ```json
   "tokenIn": "0x6f7C932e7684666C9fd1d44527765433e01fF61d9"
   ```

**Impact:**
Transactions will fail due to invalid addresses.

**Fix Required:**
Validate all addresses and fix typos.

---

### HIGH-3: ML Model Disabled
**File:** `arb_monitor.py`, line 11  
**Severity:** HIGH  
**Status:** 🔴 NOT FIXED

**Issue:**
```python
# from ml_config import predict_opportunity  # Commented out due to XGBoost issues
```

README claims "22% hit rate using XGBoost model" but model is disabled.

**Impact:**
- No ML-based opportunity prediction
- False advertising in README
- Opportunity detection is purely rule-based

**Fix Required:**
Either fix XGBoost integration or remove ML claims from README.

---

### HIGH-4: Test Mode Always Enabled
**File:** `arb_monitor.py`, line 23  
**Severity:** HIGH  
**Status:** 🔴 NOT FIXED

**Issue:**
```python
test_mode = True  # Set to True for testing without execution
```

This is hardcoded, not a command-line flag or config option.

**Impact:**
Bot never executes real trades, just logs opportunities.

**Fix Required:**
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Execute real trades')
args = parser.parse_args()
test_mode = not args.live
```

---

## 🟡 Medium Priority Issues

### MEDIUM-1: Unrealistic Profit Threshold
**File:** `risk_manager.py`, line 27  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issue:**
```python
self.min_profit_threshold = 0.5  # 0.5% minimum profit
```

Real arbitrage opportunities are typically 0.05-0.2%, not 0.5%.

**Impact:**
Bot will reject 90%+ of real opportunities as "unprofitable".

**Fix Required:**
```python
self.min_profit_threshold = 0.1  # 0.1% minimum profit
```

---

### MEDIUM-2: Gas Cost Calculation Hardcoded
**File:** `risk_manager.py`, line 71  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issue:**
```python
return 0.15  # Fallback estimate for Polygon gas
```

Hardcoded gas cost doesn't reflect actual conditions.

**Impact:**
Inaccurate profitability calculations.

**Fix Required:**
Implement proper gas cost calculation using current MATIC price and gas price.

---

### MEDIUM-3: No Slippage Calculation
**File:** `arb_monitor.py`, throughout  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issue:**
The bot doesn't calculate price impact/slippage based on trade size and liquidity.

**Impact:**
Large trades might have significant slippage, eating into profits.

**Fix Required:**
Implement price impact calculation:
```python
def calculate_price_impact(amount_in, reserve_in, reserve_out):
    # x * y = k constant product formula
    amount_out = (amount_in * reserve_out) / (reserve_in + amount_in)
    price_impact = (amount_in / reserve_in) * 100
    return amount_out, price_impact
```

---

### MEDIUM-4: Insufficient Tests
**File:** `test_suite.py`  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issues:**
1. References undefined functions (`deploy_contract`, `fetch_data_incremental`)
2. No smart contract tests
3. No integration tests
4. Missing pytest fixtures

**Impact:**
Cannot verify code correctness before deployment.

**Fix Required:**
Write comprehensive test suite. See ROADMAP.md Phase 2.

---

### MEDIUM-5: No Transaction Simulation
**File:** `arb_monitor.py`  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issue:**
Bot builds and sends transactions without simulating them first.

**Impact:**
Failed transactions waste gas fees ($0.50-$2.00 each).

**Fix Required:**
```python
# Simulate transaction before sending
try:
    w3.eth.call(tx, block_identifier='latest')
except Exception as e:
    logging.warning(f"Simulation failed: {e}")
    continue  # Don't send transaction
```

---

## 🟢 Low Priority Issues (Polish)

### LOW-1: Redis Connection Not Resilient
**File:** `arb_monitor.py`, line 86  
**Severity:** LOW  
**Status:** 🔴 NOT FIXED

**Issue:**
If Redis is down, bot crashes instead of degrading gracefully.

**Fix Required:**
Add connection retry logic and fallback to in-memory cache.

---

### LOW-2: Logging Improvements Needed
**File:** Multiple files  
**Severity:** LOW  
**Status:** 🔴 NOT FIXED

**Issue:**
- No structured logging (JSON format)
- No log rotation
- Missing important context (transaction hashes, etc.)

**Fix Required:**
Implement structured logging with Python's logging module.

---

### LOW-3: No Health Check Endpoint
**File:** `arb_monitor.py`  
**Severity:** LOW  
**Status:** 🔴 NOT FIXED

**Issue:**
No way to check if bot is running healthy without looking at logs.

**Fix Required:**
Add HTTP health check endpoint:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'ok', 'last_check': time.time()}

# Run in separate thread
```

---

### LOW-4: Telegram Bot Error Handling
**File:** `telegram_bot.py`  
**Severity:** LOW  
**Status:** 🔴 NOT FIXED

**Issue:**
Database queries can fail if DB is locked or corrupted, crashing the bot.

**Fix Required:**
Add try-except blocks around all database operations.

---

### LOW-5: No Alerting for Critical Events
**File:** All files  
**Severity:** LOW  
**Status:** 🔴 NOT FIXED

**Issue:**
No alerts sent for:
- Emergency stop triggered
- Daily loss limit exceeded
- RPC connection failures
- Smart contract errors

**Fix Required:**
Add Telegram alerts for critical events.

---

## Documentation Issues

### DOC-1: Misleading Profit Claims
**File:** `README.md` (original)  
**Severity:** HIGH  
**Status:** 🟡 PARTIALLY FIXED

**Issue:**
README claimed "$840-$975/month profit" and "22% hit rate" without basis in reality.

**Status:** Fixed in current PR, but needs user confirmation.

---

### DOC-2: Missing Prerequisites
**File:** `README.md`  
**Severity:** MEDIUM  
**Status:** 🔴 NOT FIXED

**Issue:**
README doesn't mention required:
- Solidity compiler for contract compilation
- Redis server running
- Sufficient MATIC for gas
- Testing capital for testnet

**Fix Required:**
Add complete prerequisites section.

---

## Summary

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 5     | 0     | 5         |
| High     | 4     | 0     | 4         |
| Medium   | 5     | 0     | 5         |
| Low      | 5     | 0     | 5         |
| Documentation | 2 | 1 | 1 |
| **Total** | **21** | **1** | **20** |

**Overall Status:** 🔴 NOT PRODUCTION READY

---

## Prioritized Fix Order

If you decide to fix these issues, tackle them in this order:

1. **CRITICAL-1**: Implement flash loan repayment
2. **CRITICAL-2**: Fix flash loan callback interfaces
3. **CRITICAL-3**: Add token approvals
4. **CRITICAL-4**: Add access controls
5. **HIGH-1**: Add trading paths to config
6. **HIGH-2**: Fix invalid token addresses
7. **CRITICAL-5**: Implement real price fetching
8. **HIGH-4**: Make test mode configurable
9. **MEDIUM-4**: Add comprehensive tests
10. **Deploy to testnet and test thoroughly**

Do not proceed to items 11+ until testnet testing proves profitability.

---

*Last Updated: October 10, 2025*
