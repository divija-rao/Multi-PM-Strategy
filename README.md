# Multi-PM-Strategy

## Overview
The Multi-PM-Strategy is a QuantConnect-based trading algorithm that implements a multi-asset portfolio inspired by the Merrill Lynch Investment Clock and Citadel’s Multi-Strategy model. Developed by Divija Balasankula and Sophia (Qiao) Feng at NC State University, this project leverages economic cycle detection (Recovery, Overheat, Stagflation, Reflation) to manage a diversified portfolio including forex (EUR/USD), equity pairs (NVDA/AMD), bonds (IEF), and gold (GLD). Trade data from 2020–2025 shows strong performance, with an 18% CAGR reflecting the strategy’s ability to navigate diverse market conditions.

Learn more in my Medium article, written by Divija Balasankula [Multi PM Trading Strategy on QuantConnect](https://medium.com/p/7bb60c469da4)

## Features
- **Cycle-Adaptive Portfolio**: Adjusts allocations based on economic indicators like GDP growth, unemployment, and inflation.
- **Multi-Asset Approach**: Combines forex momentum, equity pairs trading, and safe-haven assets (bonds, gold).
- **Risk Management**: Implements stop-losses (3% on EUR/USD, 5% on GLD), volatility-based rebalancing, and leverage caps (1.5–3x).
- **Backtesting**: Utilizes QuantConnect’s tools to simulate performance across key market periods: COVID-19 Pandemic (2020), Post-COVID Run-up (2020-2021), Meme Season (2021), Russia-Ukraine Conflict (2022), and AI Boom (2022-2025).

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/divija-rao/Multi-PM-Strategy.git
   cd Multi-PM-Strategy
   ```

2. **Set Up QuantConnect Environment**
   - Install the QuantConnect LEAN engine: Follow [QuantConnect’s setup guide](https://www.quantconnect.com/docs/v2/lean-cli/getting-started).
   - Ensure Python 3.7+ is installed with required libraries:
     ```bash
     pip install pandas numpy
     ```

3. **Prepare Data**
   - Place asset data in `assets_data.ipynb` and economic indicators in `economic_indicators_data.ipynb`.
   - Update `main.py` with your QuantConnect API credentials and data paths.

4. **Run the Algorithm**
   ```bash
   lean backtest main.py --output results.json
   ```

## Usage
- Edit `main.py` to customize cycle thresholds, leverage, or asset allocations.
- Analyze backtest results in `results.json` for performance metrics (e.g., rolling Sharpe ratio averaging ~10).
- Explore Jupyter notebooks (`assets_data.ipynb`, `economic_indicators_data.ipynb`) for data preprocessing and visualization.

## Project Structure
- `README.md`: This file.
- `assets_data.ipynb`: Notebook for asset price data (NVDA, AMD, IEF, GLD, EUR/USD).
- `economic_indicators_data.ipynb`: Notebook for economic indicators (GDP, unemployment, etc.).
- `main.py`: Core trading algorithm implementation.
- `requirements.txt`: List of Python dependencies.

## Trade Performance
The Multi-PM-Strategy delivers consistent risk-adjusted returns, achieving a rolling Sharpe ratio averaging around 10 with a peak above 20 in 2025 across diverse market conditions from 2020 to 2025, demonstrating its robustness. It achieved an 18% CAGR, driven by NVDA and AMD contributions, despite a maximum drawdown of 47% in 2025, mitigated by IEF gains, highlighting the strength of its diversification. Trade stats from 2020–2025 show 951 total orders (846 filled, 95 invalid), with 337 unique trades; 58% of trades were liquidated due to stringent risk controls, indicating an area for refinement in balancing risk and opportunity, while 10% invalid orders suggest potential improvements in data quality or execution logic. Additionally, 10 margin calls occurred, underscoring the need for enhanced leverage management.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit changes (`git commit -m "Add feature-name"`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

## Acknowledgments
- Inspired by Merrill Lynch’s Investment Clock and Citadel’s Multi-Strategy model.
- Built as part of a course at NC State University, under the guidance of Prof. Robert G. Carroll, Senior Vice President at QMS Capital Management, a quantitative hedge fund.

## Contact
For questions or collaboration, reach out to drbalasa@ncstate.edu
