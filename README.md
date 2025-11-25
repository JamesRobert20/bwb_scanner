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
python -m pytest tests/ -v
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
SPY     2025-11-28   3   440  445  455    2.00      700.00    300.00  233.33
SPY     2025-11-28   3   438  444  456    1.80      680.00    320.00  212.50
...

Summary Statistics:
====================================================================================================
Total Positions: 45
Avg Score: 185.50
Avg Credit: 1.65
Avg Max Profit: 665.00
Avg Max Loss: 335.00
Best Score: 233.33
Worst Score: 125.00
```

## API & Full-Stack Mode

The BWB Scanner includes a FastAPI backend that can be consumed by web frontends.

### Running the API Server

Start the API server locally:

```bash
python main.py --api
```

The API will be available at:
- **Base URL**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### API Endpoints

#### GET /
Health check endpoint.

**Response:**
```json
{
  "message": "BWB Scanner API ready"
}
```

#### GET /tickers
List supported tickers and their spot prices.

**Response:**
```json
{
  "supported_tickers": ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD"],
  "spot_prices": {"SPY": 450.0, "QQQ": 380.0, ...}
}
```

#### POST /scan
Scan for BWB opportunities.

**Request Body:**
```json
{
  "ticker": "SPY",
  "expiry": "2025-11-30"
}
```

**Response:**
```json
{
  "results": [
    {
      "ticker": "SPY",
      "expiry": "2025-11-30",
      "dte": 5,
      "k1": 440.0,
      "k2": 445.0,
      "k3": 455.0,
      "wing_left": 5.0,
      "wing_right": 10.0,
      "credit": 2.0,
      "max_profit": 700.0,
      "max_loss": 300.0,
      "score": 233.33
    }
  ],
  "summary": {
    "total_found": 45,
    "avg_score": 150.5,
    "best_score": 233.33,
    "avg_credit": 1.85
  }
}
```

#### GET /health
Service health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "bwb-scanner-api",
  "version": "1.0.0"
}
```

### Testing the API with curl

```bash
# Health check
curl http://localhost:8000/

# Scan all expiries for SPY
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"ticker": "SPY"}'

# Scan specific expiry
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"ticker": "SPY", "expiry": "2025-11-30"}'
```

### Local Development

Run the API server locally for development:

```bash
python main.py --api
```

This will start the API service at `http://localhost:8000` with hot-reload enabled.

### CORS Configuration

The API is configured with CORS enabled for all origins in development mode. For production, set the `ALLOWED_ORIGINS` environment variable in Vercel to restrict allowed origins:

```bash
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-custom-domain.com
```

If not set, it defaults to `*` (allow all origins) for development.

## Project Structure

```
bwb_scanner/
├── bwb_scanner/
│   ├── __init__.py           # Package initialization
│   ├── api.py                # FastAPI REST API
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
├── api/                      # Vercel serverless functions
│   └── index.py             # Vercel API handler
├── vercel.json               # Vercel deployment configuration
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
- **Max Profit**: (Net credit + left wing width) × 100 (occurs at K2)
- **Max Loss**: (Right wing - left wing - credit) × 100 (occurs above K3 for typical BWB)
- **Score**: Max Profit / Max Loss × 100 (higher is better)

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

## 🚢 Deployment

### Vercel (Recommended)

Deploy the FastAPI backend as serverless functions on Vercel:

#### Option 1: Deploy via Vercel Dashboard

1. Push your code to GitHub/GitLab/Bitbucket
2. Go to [vercel.com](https://vercel.com) and sign in
3. Click "New Project" and import your repository
4. Vercel will detect Python and use the `vercel.json` configuration
5. Click "Deploy"

#### Option 2: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy (first time)
vercel

# Deploy to production
vercel --prod
```

#### Configuration

The project includes:
- `vercel.json` - Vercel configuration for Python serverless functions
- `api/index.py` - Serverless function entry point
- `requirements.txt` - Python dependencies

#### API Endpoints After Deployment

Once deployed, your API will be available at:
- `https://your-project.vercel.app/` - Root endpoint
- `https://your-project.vercel.app/scan` - Scan endpoint
- `https://your-project.vercel.app/health` - Health check
- `https://your-project.vercel.app/docs` - Interactive API documentation

#### Environment Variables

Set these in your Vercel project settings:

- `ALLOWED_ORIGINS` - Comma-separated list of allowed frontend origins (e.g., `https://your-frontend.vercel.app,https://your-custom-domain.com`). Defaults to `*` for development.

The CORS configuration automatically adapts based on this environment variable:
- If `ALLOWED_ORIGINS` is `*` or not set: Allows all origins (development mode)
- If `ALLOWED_ORIGINS` is set to specific domains: Only allows those origins (production mode)

#### Sample Data

The API generates synthetic options data in memory at startup for all supported tickers. This data is used for demonstration purposes. For production, integrate with a real market data provider.

### Other Deployment Options

- **Railway**: Supports Python with FastAPI out of the box
- **Render**: Free tier available for Python web services
- **Fly.io**: Good for containerized Python apps

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

The project includes a comprehensive test suite with 77 tests covering:

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
- ✅ **Payoff-at-underlying tests** (validates P&L at various spot prices)

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
# Long 440 @ $12 ask, Short 2x 445 @ $8 bid, Long 455 @ $2 ask
# Credit = (2*8) - 12 - 2 = $2.00
# Wing left = 5, Wing right = 10
# Max Profit at K2 = ($2.00 + $5.00) * 100 = $700
# Max Loss above K3 = (10 - 5 - 2) * 100 = $300
# Score = $700 / $300 * 100 = 233.33
```

**Filter Verification:**
```python
# Tests confirm:
# - DTE filter: Only 1-10 day positions included
# - Delta filter: Short strike delta 0.20-0.35
# - Credit filter: Minimum $0.50 credit
# - Asymmetry filter: (K2-K1) ≠ (K3-K2)
# - Data validation: bid <= ask, prices >= 0, valid delta ranges
```

## Disclaimer

This software is for educational purposes only. Options trading involves substantial risk of loss. Always conduct your own research and consult with a financial advisor before trading.