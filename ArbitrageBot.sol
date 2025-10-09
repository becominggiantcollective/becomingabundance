// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IUniswapV2Router {
    function swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external returns (uint256[] memory amounts);
}

interface IFlashLoanProvider {
    function flashLoan(address receiver, address token, uint256 amount, bytes calldata data) external;
}

contract ArbitrageBot is ReentrancyGuard, Ownable {
    address[] public dexes;
    address[] public loanProviders;
    uint256 public minProfit;
    uint256 public maxSlippage = 700; // 0.7%

    constructor(address[] memory _dexes, address[] memory _loanProviders, uint256 _minProfit) {
        dexes = _dexes;
        loanProviders = _loanProviders;
        minProfit = _minProfit;
    }

    function executeArbitrage(address tokenIn, address tokenOut, uint256 amount, address[] memory path, address dex, address loanProvider) external onlyOwner nonReentrant {
        require(amount > 0, "Invalid amount");
        bytes memory data = abi.encode(tokenIn, tokenOut, amount, path, dex);
        IFlashLoanProvider(loanProvider).flashLoan(address(this), tokenIn, amount, data);
    }

    function flashLoanCallback(address token, uint256 amount, bytes memory data) external {
        (address tokenIn, address tokenOut, uint256 amountIn, address[] memory path, address dex) = abi.decode(data, (address, address, uint256, address[], address));
        uint256[] memory amounts = IUniswapV2Router(dex).swapExactTokensForTokens(amountIn, amountIn * (1000 - maxSlippage) / 1000, path, address(this), block.timestamp + 60);
        require(amounts[amounts.length - 1] >= amount + minProfit, "Not profitable");
        // Repay flash loan (simplified)
    }

    function swapUniswapV3(address pool, uint256 amountIn, uint256 minOut) external onlyOwner {
        // Uniswap V3 swap logic (simplified)
    }
}