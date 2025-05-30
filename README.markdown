# Multi-PM-Strategy

## Overview
The Multi-PM-Strategy is a QuantConnect-based trading algorithm that implements a multi-asset portfolio inspired by the Merrill Lynch Investment Clock and Citadel’s Multi-Strategy model. Developed by Divija Balasankula and Sophia (Qiao) Feng at NC State University, this project leverages economic cycle detection (Recovery, Overheat, Stagflation, Reflation) to manage a diversified portfolio including forex (EUR/USD), equity pairs (NVDA/AMD, with alternatives like KO/PEP or LOW/HD considered), bonds (IEF), and gold (GLD). Trade data from 2020–2025 shows solid activity, with a Sharpe ratio of approximately 1.0–1.3, reflecting the strategy’s ability to navigate diverse market conditions.

## Features
- **Cycle-Adaptive Portfolio**: Adjusts allocations based on economic indicators like GDP growth, unemployment, and inflation.
- **Multi-Asset Approach**: Combines forex momentum, equity pairs trading, and safe-haven assets (bonds, gold).
- **Risk Management**: Implements stop-losses (3% on EUR/USD, 5% on GLD), volatility-based rebalancing, and leverage caps (1.5–3x).
- **Backtesting**: Utilizes QuantConnect’s tools to simulate performance across five periods (e.g., 2020 Q1 COVID crash, 2022 USD rally).

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
- Analyze backtest results in `results.json` for performance metrics (e.g., Sharpe ratio ~1.0–1.3).
- Explore Jupyter notebooks (`assets_data.ipynb`, `economic_indicators_data.ipynb`) for data preprocessing and visualization.

## Project Structure
- `README.md`: This file.
- `assets_data.ipynb`: Notebook for asset price data (NVDA, AMD, IEF, GLD, EUR/USD).
- `economic_indicators_data.ipynb`: Notebook for economic indicators (GDP, unemployment, etc.).
- `main.py`: Core trading algorithm implementation.
- `requirements.txt`: List of Python dependencies.

## Performance
The Multi-PM-Strategy excels in delivering consistent risk-adjusted returns, achieving a rolling Sharpe ratio of 1.0–1.3 across diverse market conditions from 2020 to 2025, demonstrating its robustness. It successfully navigated challenges like the 2020 Q1 COVID crash, with IEF gains offsetting a ~12% drawdown, showcasing the strength of its diversification. However, 58% of the 337 trades were liquidated due to stringent risk controls, which, while protective, highlight an area for refinement in balancing risk and opportunity. Additionally, 26% of trades were marked invalid, likely due to execution or data issues, suggesting potential improvements in data quality or trade execution logic.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit changes (`git commit -m "Add feature-name"`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

## License
This project is open-source under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Inspired by Merrill Lynch’s Investment Clock and Citadel’s Multi-Strategy model.
- Built as part of the FIM590 course at NC State University, presented on March 25, 2025, under the guidance of Prof. Robert G. Carroll, Senior Vice President at a hedge fund.

## Contact
For questions or collaboration, reach out to divija-rao@ncstate.edu or sophia-feng@ncstate.edu.