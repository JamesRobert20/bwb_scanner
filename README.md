# BWB Scanner - Broken Wing Butterfly Options Strategy Scanner

A production-ready Python application that scans options chains to identify profitable Broken Wing Butterfly (BWB) opportunities for call options.

## Overview

The BWB Scanner analyzes options chain data to find asymmetric butterfly spreads that meet specific risk/reward criteria. It focuses on call options with near-term expiration (1-10 DTE) and identifies positions with favorable credit profiles.

### What is a Broken Wing Butterfly?

A Broken Wing Butterfly is an options strategy consisting of:
- **Long 1 call** at strike K1 (lower strike)
- **Short 2 calls** at strike K2 (middle strike)
- **Long 1 call** at strike K3 (upper strike)

The "broken wing" refers to asymmetric wing widths: `(K2 - K1) ≠ (K3 - K2)`

This asymmetry allows the position to be opened for a net credit while maintaining defined risk.

## Features

- ✅ **Clean Architecture**: Separation of concerns with dedicated modules for data loading, strategy validation, and scanning
- ✅ **Type Hints**: Full type annotations for better IDE support and code clarity
- ✅ **Realistic Data Generation**: Built-in generator for testing with realistic bid/ask spreads, deltas, and IVs
- ✅ **Flexible Filtering**: Configurable DTE, delta, and credit requirements
- ✅ **Risk Metrics**: Calculates max profit, max loss, and risk/reward score for each position
- ✅ **Sorted Results**: Automatically ranks positions by score (max_profit / max_loss)
- ✅ **CSV Export**: Saves results for further analysis

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. Clone or download this repository:
```bash
cd bwb_scanner
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Run tests to verify installation:
```bash
pytest tests/ -v
```

## Usage

### Generate Sample Data

First, generate realistic sample options chain data:

```bash
python main.py --generate-sample
```

This creates `sample_options_chain.csv` with SPY options data including:
- Multiple expiries (3, 5, 7, 10 DTE)
- 30 strike prices around current spot price
- Both calls and puts
- Realistic bid/ask spreads, deltas, and implied volatilities

### Scan for BWB Opportunities

Scan all expiries for a ticker:

```bash
python main.py --csv sample_options_chain.csv --ticker SPY
```

Scan a specific expiry:

```bash
python main.py --csv sample_options_chain.csv --ticker SPY --expiry 2025-11-28
```

### Output

The scanner displays:
1. **Top 10 positions** sorted by score (best first)
2. **Summary statistics** including average metrics and best/worst scores
3. **Full results CSV** saved as `bwb_results_{TICKER}.csv`

Example output:
```
Scanning for BWB opportunities in SPY...

Found 45 valid BWB positions

Top 10 BWB Positions (sorted by score):
====================================================================================================
ticker  expiry      dte   k1   k2   k3  credit  max_profit  max_loss  score
SPY     2025-11-28   3   440  445  455    1.25      125.00    875.00  0.1429
SPY     2025-11-28   3   438  444  456    1.18      118.00    882.00  0.1338
...

Summary Statistics:
====================================================================================================
Total Positions: 45
Avg Score: 0.1156
Avg Credit: 0.98
Avg Max Profit: 98.45
Avg Max Loss: 865.22
Best Score: 0.1429
Worst Score: 0.0571
```

## Project Structure

```
bwb_scanner/
├── bwb_scanner/
│   ├── __init__.py           # Package initialization
│   ├── data_loader.py        # CSV loading and validation
│   ├── data_generator.py     # Sample data generation
│   ├── strategy.py           # BWB validation and construction
│   └── scanner.py            # Main scanning orchestration
├── tests/
│   ├── __init__.py           # Test package initialization
│   ├── test_strategy.py      # Strategy logic tests
│   ├── test_data_loader.py   # Data loading tests
│   └── test_scanner.py       # Scanner integration tests
├── main.py                   # CLI entry point
├── example_usage.py          # Programmatic usage examples
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Key Assumptions

### Strategy Constraints
- **DTE Range**: 1-10 days (near-term expiration for higher theta decay)
- **Delta Range**: 0.20-0.35 for short strike (targeting OTM positions)
- **Minimum Credit**: $0.50 net credit required
- **Asymmetry**: Wings must be unequal `(K2-K1) ≠ (K3-K2)`
- **Option Type**: Call options only

### Data Assumptions
- Bid/ask prices are executable (no slippage consideration)
- All strikes in the chain are liquid and tradeable
- Greeks (delta, IV) are accurate at time of scan
- No transaction costs or commissions included
- Single contract multiplier of 100

### Risk Calculations
- **Max Profit**: Net credit received × 100
- **Max Loss**: Larger wing width × 100 - Max Profit
- **Score**: Max Profit / Max Loss (higher is better)

## Future Improvements

For a production trading system, consider adding:

### 1. Enhanced Risk Metrics
- **Probability of Profit (POP)**: Using delta as proxy or full Monte Carlo simulation
- **Greeks Analysis**: Theta, gamma, vega exposure for position management
- **Break-even Points**: Calculate exact break-even prices
- **Expected Value**: Probability-weighted profit/loss

### 2. Real-time Data Integration
- **Live Market Data**: Integration with broker APIs (Interactive Brokers, TD Ameritrade)
- **Real-time Greeks**: Dynamic greek calculations using Black-Scholes or binomial models
- **Bid/Ask Monitoring**: Track spread changes and liquidity
- **Volatility Surface**: Build and analyze IV surface for better pricing

### 3. Advanced Filtering
- **Liquidity Filters**: Open interest and volume requirements
- **Spread Width Limits**: Maximum bid/ask spread tolerance
- **IV Rank/Percentile**: Filter by relative volatility levels
- **Earnings Avoidance**: Exclude positions with earnings in DTE window

### 4. Portfolio Management
- **Position Sizing**: Kelly criterion or fixed fractional sizing
- **Correlation Analysis**: Avoid over-concentration in correlated underlyings
- **Margin Requirements**: Calculate and track margin usage
- **P&L Tracking**: Monitor open positions and historical performance

### 5. Execution Features
- **Order Management**: Automated order placement with limit orders
- **Adjustment Rules**: Automated position adjustments based on P&L or delta
- **Exit Strategies**: Profit targets and stop losses
- **Rolling Logic**: Automatic position rolling before expiration

### 6. Backtesting & Analysis
- **Historical Backtesting**: Test strategy on historical options data
- **Performance Metrics**: Sharpe ratio, max drawdown, win rate
- **Scenario Analysis**: Stress testing under different market conditions
- **Optimization**: Parameter tuning for different market regimes

### 7. Monitoring & Alerts
- **Real-time Alerts**: Notify when new opportunities meet criteria
- **Position Monitoring**: Track P&L and risk metrics for open positions
- **Market Regime Detection**: Adjust parameters based on VIX or other indicators
- **Dashboard**: Web interface for visualization and management

### 8. Data Quality
- **Data Validation**: More robust checks for stale or invalid data
- **Error Handling**: Graceful degradation when data is missing
- **Logging**: Comprehensive logging for debugging and audit trails
- **Testing**: Unit tests, integration tests, and property-based testing

## Technical Details

### Module Responsibilities

**data_loader.py**
- Validates CSV structure and data types
- Filters options by ticker, expiry, and type
- Handles missing data gracefully

**strategy.py**
- `BWBValidator`: Enforces strategy constraints (DTE, delta, credit)
- `BWBCalculator`: Computes position metrics (credit, profit, loss, score)
- `BWBConstructor`: Finds all valid combinations in options chain
- `BWBPosition`: Data class representing a single position

**scanner.py**
- Orchestrates the scanning workflow
- Combines filtering, validation, and calculation
- Generates sorted results and summary statistics

**data_generator.py**
- Creates realistic synthetic options data
- Models volatility smile and term structure
- Generates appropriate bid/ask spreads

## Performance Considerations

- **Combination Complexity**: For N strikes, evaluates O(N³) combinations
- **Optimization**: Early filtering reduces combinations checked
- **Memory**: Efficient pandas operations for large datasets
- **Scalability**: Can process thousands of options in seconds

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Areas for improvement:
- Additional strategy types (put BWBs, iron condors, etc.)
- More sophisticated pricing models
- Real-time data connectors
- Web interface
- Backtesting framework

## Testing

The project includes a comprehensive test suite with 68 tests covering:

### Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_strategy.py -v
```

Run with coverage report:
```bash
pytest tests/ --cov=bwb_scanner --cov-report=html
```

### Test Coverage

**Strategy Tests** ([`test_strategy.py`](tests/test_strategy.py:1))
- ✅ Validator initialization and configuration
- ✅ DTE, delta, credit, and asymmetry validation
- ✅ **Payoff math verification with known examples**
- ✅ Credit, max profit, max loss calculations
- ✅ Score calculation and edge cases
- ✅ Position construction and filtering

**Data Loader Tests** ([`test_data_loader.py`](tests/test_data_loader.py:1))
- ✅ CSV loading and validation
- ✅ Missing columns and invalid data handling
- ✅ Data type conversion and normalization
- ✅ Ticker and expiry filtering
- ✅ Call/put filtering

**Scanner Tests** ([`test_scanner.py`](tests/test_scanner.py:1))
- ✅ Scanner initialization and configuration
- ✅ **Filter behavior verification** (DTE, delta, credit, asymmetry)
- ✅ End-to-end scanning workflow
- ✅ Results sorting and statistics
- ✅ Edge cases (empty results, missing data)

### Key Test Examples

**Payoff Math Verification:**
```python
# Known example: 440/445/455 BWB
# Long 440 @ $15, Short 2x 445 @ $8, Long 455 @ $3
# Credit = 15 + 3 - (2*8) = $2.00
# Max Profit = $2.00 * 100 = $200
# Max Loss = (10 * 100) - $200 = $800
# Score = $200 / $800 = 0.25
```

**Filter Verification:**
```python
# Tests confirm:
# - DTE filter: Only 1-10 day positions included
# - Delta filter: Short strike delta 0.20-0.35
# - Credit filter: Minimum $0.50 credit
# - Asymmetry filter: (K2-K1) ≠ (K3-K2)
```

## Disclaimer

This software is for educational purposes only. Options trading involves substantial risk of loss. Always conduct your own research and consult with a financial advisor before trading.