# Backtesting Methodology

This document records the methodology required to interpret the research artifacts in this repository. Until each item below is explicitly populated and validated, the included outputs should be treated as illustrative research outputs rather than independently verified investment-performance records.

## Dataset

- Provider: `yfinance` for downloaded OHLCV data.
- Start and end dates: strategy/report specific; not yet normalized into one canonical run manifest.
- Adjustment policy: current downloader stores Yahoo `Open`, `High`, `Low`, `Close`, and `Volume` with `auto_adjust=False`; adjusted-close treatment is not yet modeled.
- Missing-data policy: strategy dependent; formal missing-row and missing-OHLCV handling tests are pending.
- Time zone: India market logic uses `Asia/Kolkata` for complete-candle decisions.
- Universe source: static ticker lists in `trading_bot.utility`.
- Point-in-time membership: not implemented. Current universe lists may introduce survivorship bias when used historically.

## Signal Timing

- Signal observation time: strategy dependent, generally evaluated on completed daily or weekly candles.
- Earliest permissible execution: not yet standardized in all historical runners.
- Execution price: strategy/report specific; must be checked before interpreting each result.
- Weekly-candle completion rule: complete-candle helper exists for current scans; dedicated regression coverage for Monday-Thursday daily alignment is pending.

## Portfolio Simulation

- Initial capital: strategy/report specific.
- Position size: strategy/report specific.
- Maximum concurrent positions: strategy/report specific.
- Capital reservation: implemented in the c5/c6 simulation, but assumptions require independent review.
- Candidate-ranking rule: current c5/c6 simulation uses strategy weights and preselected holding-horizon proxies. These must be based only on information available before entry to avoid look-ahead leakage.
- Tie-breaking rule: deterministic sorting should be documented per simulation.
- Rejected-order behavior: skipped trades are reported in the c5/c6 simulation, but detailed audit trails are not yet standardized.

## Costs

The current curated artifacts should not be assumed to include:

- Brokerage
- Securities transaction tax
- Exchange transaction charges
- GST
- SEBI charges
- Stamp duty
- Bid-ask spread
- Slippage
- Market impact
- Partial fills
- Liquidity constraints

## Bias Controls

- Look-ahead prevention: partial safeguards exist for latest complete candles; full regression coverage is pending.
- Survivorship-bias treatment: not solved because point-in-time index membership is not implemented.
- Parameter-selection process: not yet separated into train, validation, and test periods.
- Train/validation/test periods: not yet formalized.
- Multiple-testing treatment: not yet formalized.

## Metrics

Each headline result should state:

- CAGR
- Maximum drawdown
- Volatility
- Sharpe or Sortino methodology
- Exposure
- Turnover
- Benchmark
- Transaction-cost assumptions
- Capital reuse and concurrent-position assumptions
- Whether parameters were selected using the same sample

## Data and Artifact Licensing

The software source code is provided under the repository license. Downloaded market data remains subject to the terms of its original provider. Committed fixture data and generated research artifacts are included solely to reproduce and review the software's behavior.
