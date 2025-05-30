from AlgorithmImports import *
import pandas as pd
import numpy as np
from io import StringIO
from datetime import timedelta, datetime

class MultiPMTradingAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(datetime(2025, 5, 29))
        self.SetCash(100000)  
        # Assets
        self.forex = self.AddForex("EURUSD", Resolution.Daily, Market.FXCM).Symbol
        self.nvda = self.AddEquity("NVDA", Resolution.Daily).Symbol
        self.amd = self.AddEquity("AMD", Resolution.Daily).Symbol
        self.ief = self.AddEquity("IEF", Resolution.Daily).Symbol
        self.gld = self.AddEquity("GLD", Resolution.Daily).Symbol
        self.vix = self.AddData(Fred, "VIXCLS", Resolution.Daily).Symbol
        self.SetWarmup(60, Resolution.Daily)
        # Data
        self.asset_data = None
        self.economic_data = None
        try:
            asset_csv = self.ObjectStore.Read("Asset_Data")
            if asset_csv:
                self.asset_data = pd.read_csv(StringIO(asset_csv), parse_dates=["Date"], index_col="Date")
            economic_csv = self.ObjectStore.Read("Economic_Indicators")
            if economic_csv:
                self.economic_data = pd.read_csv(StringIO(economic_csv), parse_dates=["Date"], index_col="Date")
        except Exception as e:
            self.Debug(f"Error loading data: {str(e)}")
        # Training and trading periods
        self.training_start_date = datetime(2017, 1, 1)
        self.training_end_date = datetime(2018, 12, 31)
        self.is_training = True
        self.training_completed = False
        # State
        self.previous_cycle = "Recovery"
        self.forex_position = None
        self.pairs_position = None
        self.gld_high = None
        self.forex_entry_price = None
        self.pairs_spread_high = None
        self.nvda_high = None
        self.amd_high = None
        self.lookback = 15
        self.base_drawdown_limit = float(self.GetParameter("base_drawdown_limit", 0.03))  # Tightened to 0.03
        self.atr_multiplier = float(self.GetParameter("atr_multiplier", 1.5))  # Increased to 1.5
        self.pairs_trailing_stop = float(self.GetParameter("pairs_trailing_stop", 0.03))  # Increased to 0.03
        self.initial_equity = self.Portfolio.TotalPortfolioValue
        self.trade_count = {"Forex": 0, "Pairs": 0}
        self.cycle_confirm_days = 0
        self.cycle_candidate = "Recovery"
        self.drawdown_pause_days = 0
        self.max_portfolio_leverage = 1.5
        self.last_trade_time = self.Time
        self.trade_cooldown = timedelta(days=1)
        self.rebalance_frequency = 5
        self.last_rebalance = self.Time
        # Allocations
        self.allocations = {
            "Recovery": {"Forex": 0.30, "EquityPair": 0.60, "Bond": 0.05, "Gold": 0.05},  # Adjusted for more EquityPair
            "Overheat": {"Forex": 0.10, "EquityPair": 0.10, "Bond": 0.40, "Gold": 0.40},
            "Stagflation": {"Forex": 0.25, "EquityPair": 0.15, "Bond": 0.30, "Gold": 0.30},
            "Reflation": {"Forex": 0.30, "EquityPair": 0.60, "Bond": 0.05, "Gold": 0.05}
        }
        self.leverage = {"Forex": 2.0, "EquityPair": 3.0, "Bond": 1.0, "Gold": 1.0}  # Increased leverage
        self.allocation_history = pd.DataFrame(columns=["Date", "Forex", "EquityPair", "Bond", "Gold"])
        self.trade_log = []
        # Optimization variables
        self.z_score_entry = 1.0
        self.momentum_threshold = 0.00007
        self.simulated_equity = 100000
        self.best_simulated_equity = 100000
        self.best_z_score_entry = self.z_score_entry
        self.best_momentum_threshold = self.momentum_threshold
        self.z_score_options = [0.8, 1.0, 1.2]
        self.momentum_options = [0.00005, 0.00007, 0.00009]
        self.current_params = {"z_score_entry": self.z_score_entry, "momentum_threshold": self.momentum_threshold}
        self.param_combinations = [(z, m) for z in self.z_score_options for m in self.momentum_options]
        self.current_combination_index = 0
        self.simulated_positions = {}
        self.training_cycle_equity = {}
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(0, 0), self.ResetEquity)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), self.TimeRules.At(0, 0), self.Rebalance)
        self.RunTraining()

    def RunTraining(self):
        self.Debug("Starting training phase...")
        training_days = (self.training_end_date - self.training_start_date).days
        forex_prices = self.History(self.forex, training_days + self.lookback + 20, Resolution.Daily)
        vix_prices = self.History(self.vix, training_days + 2, Resolution.Daily)
        history = self.History([self.nvda, self.amd], training_days + self.lookback + 20, Resolution.Daily)

        if forex_prices.empty or vix_prices.empty or history.empty:
            self.Debug("Error: Insufficient historical data for training")
            self.is_training = False
            self.training_completed = True
            return

        forex_prices = forex_prices.reset_index().set_index('time')
        vix_prices = vix_prices.reset_index().set_index('time')
        history = history.reset_index().set_index('time')

        for i in range(len(self.param_combinations)):
            z_score_entry, momentum_threshold = self.param_combinations[i]
            self.current_params = {"z_score_entry": z_score_entry, "momentum_threshold": momentum_threshold}
            self.simulated_equity = 100000
            self.simulated_positions = {}

            for day in pd.date_range(self.training_start_date, self.training_end_date):
                current_date = day.date()
                vix_slice = vix_prices[vix_prices.index.date <= current_date].tail(2)
                vix_value = vix_slice["value"].iloc[-1] if not vix_slice.empty and "value" in vix_slice.columns else 20
                vix_momentum = (vix_slice["value"].iloc[-1] - vix_slice["value"].iloc[-2]) / vix_slice["value"].iloc[-2] if len(vix_slice) >= 2 else 0

                forex_slice = forex_prices[forex_prices.index.date <= current_date].tail(self.lookback + 20)
                if not forex_slice.empty and "close" in forex_slice.columns and len(forex_slice) >= self.lookback:
                    prices = forex_slice["close"]
                    momentum = self.CalculateMomentum(prices, self.lookback)
                    atr = self.CalculateATR(prices, self.lookback)
                    vol = self.CalculateVolatility(prices, self.lookback)
                    vol_limit = 0.03 if self.previous_cycle in ["Recovery", "Reflation"] else 0.02
                    sma_short = prices.rolling(10).mean().iloc[-1]
                    sma_long = prices.rolling(20).mean().iloc[-1]
                    forex_price = prices.iloc[-1]

                    if self.forex_position and self.forex_entry_price:
                        price_change = abs(forex_price - self.forex_entry_price) / self.forex_entry_price
                        if price_change >= self.atr_multiplier * atr:
                            self.simulated_positions.pop(self.forex, None)
                            self.forex_position = None
                            self.forex_entry_price = None

                    if self.forex_position is None and abs(momentum) > momentum_threshold and vol < vol_limit and vix_momentum < 0.15 and vix_value < 50:
                        signal = (sma_short > sma_long if momentum > 0 else sma_short < sma_long)
                        if signal:
                            self.forex_position = "Long" if momentum > 0 else "Short"
                            self.forex_entry_price = forex_price
                            adjusted_forex_weight = self.allocations[self.previous_cycle]["Forex"] * self.leverage["Forex"] * (1.0 if self.forex_position == "Long" else -1.0)
                            self.simulated_positions[self.forex] = {"weight": adjusted_forex_weight, "entry_price": forex_price}
                            self.UpdateSimulatedEquity(forex_slice, history, current_date)

                nvda_slice = history[history.index.date <= current_date].query('symbol == @self.nvda').tail(self.lookback + 20) if self.nvda in history['symbol'].values else None
                amd_slice = history[history.index.date <= current_date].query('symbol == @self.amd').tail(self.lookback + 20) if self.amd in history['symbol'].values else None
                if nvda_slice is not None and amd_slice is not None and len(nvda_slice) >= self.lookback and len(amd_slice) >= self.lookback:
                    nvda_prices = nvda_slice["close"]
                    amd_prices = amd_slice["close"]
                    nvda_price = nvda_prices.iloc[-1]
                    amd_price = amd_prices.iloc[-1]
                    spread, mean, std = self.CalculateSpread(nvda_prices, amd_prices, self.lookback)
                    z_score = (spread - mean) / std if std != 0 else 0
                    spread_vol = self.CalculateVolatility(pd.Series(spread, index=nvda_prices.index), self.lookback)

                    if self.pairs_position:
                        self.pairs_spread_high = max(self.pairs_spread_high or abs(z_score), abs(z_score))
                        self.nvda_high = max(self.nvda_high or nvda_price, nvda_price)
                        self.amd_high = max(self.amd_high or amd_price, amd_price)
                        if abs(z_score) > 3 or abs(z_score) < self.pairs_spread_high * 0.95 or abs(z_score) < 0.05:
                            self.simulated_positions.pop(self.nvda, None)
                            self.simulated_positions.pop(self.amd, None)
                            self.pairs_position = None
                            self.pairs_spread_high = None
                            self.nvda_high = None
                            self.amd_high = None
                            self.UpdateSimulatedEquity(forex_slice, history, current_date)
                        elif nvda_price < self.nvda_high * (1 - self.pairs_trailing_stop) or amd_price < self.amd_high * (1 - self.pairs_trailing_stop):
                            self.simulated_positions.pop(self.nvda, None)
                            self.simulated_positions.pop(self.amd, None)
                            self.pairs_position = None
                            self.nvda_high = None
                            self.amd_high = None
                            self.UpdateSimulatedEquity(forex_slice, history, current_date)

                    if self.pairs_position is None and abs(z_score) > z_score_entry and spread_vol < 1.5 and vix_momentum < 0.15 and vix_value < 50:
                        self.pairs_position = "LongAMDShortNVDA" if z_score > z_score_entry else "LongNVDAShortAMD"
                        self.nvda_high = nvda_price
                        self.amd_high = amd_price
                        pair_weight = self.allocations[self.previous_cycle]["EquityPair"] * self.leverage["EquityPair"] / 2
                        adjusted_nvda_weight = pair_weight if self.pairs_position == "LongNVDAShortAMD" else -pair_weight
                        adjusted_amd_weight = -pair_weight if self.pairs_position == "LongNVDAShortAMD" else pair_weight
                        self.simulated_positions[self.nvda] = {"weight": adjusted_nvda_weight, "entry_price": nvda_price}
                        self.simulated_positions[self.amd] = {"weight": adjusted_amd_weight, "entry_price": amd_price}
                        self.UpdateSimulatedEquity(forex_slice, history, current_date)

            self.training_cycle_equity[(z_score_entry, momentum_threshold)] = self.simulated_equity
            if self.simulated_equity > self.best_simulated_equity:
                self.best_simulated_equity = self.simulated_equity
                self.best_z_score_entry = z_score_entry
                self.best_momentum_threshold = momentum_threshold
            self.Debug(f"Completed simulation for z_score_entry={z_score_entry}, momentum_threshold={momentum_threshold}, equity={self.simulated_equity}")

        self.z_score_entry = self.best_z_score_entry
        self.momentum_threshold = self.best_momentum_threshold
        self.current_params = {"z_score_entry": self.z_score_entry, "momentum_threshold": self.momentum_threshold}
        self.is_training = False
        self.training_completed = True
        self.Debug(f"Training complete. Optimized z_score_entry: {self.z_score_entry}, momentum_threshold: {self.momentum_threshold}")

    def ResetEquity(self):
        if not self.is_training:
            self.initial_equity = self.Portfolio.TotalPortfolioValue
            self.trade_log.append({"Date": self.Time, "Event": f"Equity reset: {self.initial_equity}"})
        else:
            if self.current_combination_index < len(self.param_combinations):
                self.simulated_equity = 100000
                self.simulated_positions = {}

    def OnData(self, data):
        if self.IsWarmingUp or not self.training_completed:
            return
        current_date = self.Time.date()
        vix_value = self.Securities[self.vix].Price if self.vix in self.Securities else 20
        vix_momentum = 0
        vix_prices = self.History(self.vix, 2, Resolution.Daily)
        if not vix_prices.empty and "value" in vix_prices.columns and len(vix_prices) >= 2:
            vix_momentum = (vix_prices["value"].iloc[-1] - vix_prices["value"].iloc[-2]) / vix_prices["value"].iloc[-2]

        if self.drawdown_pause_days > 0:
            self.drawdown_pause_days -= 1
            return
        current_equity = self.Portfolio.TotalPortfolioValue
        drawdown_limit = self.base_drawdown_limit
        drawdown = (self.initial_equity - current_equity) / self.initial_equity
        if drawdown > drawdown_limit:
            self.Liquidate()
            self.forex_position = None
            self.pairs_position = None
            self.initial_equity = current_equity
            self.drawdown_pause_days = 5
            self.Debug(f"Drawdown exceeded: {drawdown:.2%}, pausing trading for 5 days")
            return
        if self.Portfolio.MarginRemaining < self.Portfolio.TotalPortfolioValue * 0.20:
            self.Debug("Margin too low, skipping trading")
            return
        if self.Time < self.last_trade_time + self.trade_cooldown:
            self.Debug("Trade cooldown active, skipping trading")
            return
        cycle = self.previous_cycle
        if self.economic_data is not None and current_date in self.economic_data.index:
            indicators = self.economic_data.loc[current_date]
            cycle = self.DetermineCycle(indicators, vix_value)
        forex_prices = self.History(self.forex, self.lookback + 20, Resolution.Daily)
        forex_price = self.Securities[self.forex].Price if self.Securities[self.forex].Price else (forex_prices["close"].iloc[-1] if not forex_prices.empty and "close" in forex_prices.columns and len(forex_prices) >= 1 else 0)
        if not forex_prices.empty and "close" in forex_prices.columns and len(forex_prices) >= self.lookback:
            prices = forex_prices["close"]
            momentum = self.CalculateMomentum(prices, self.lookback)
            sma_short = prices.rolling(10).mean().iloc[-1]
            sma_long = prices.rolling(20).mean().iloc[-1]
            atr = self.CalculateATR(prices, self.lookback)
            vol = self.CalculateVolatility(prices, self.lookback)
            vol_limit = 0.03 if cycle in ["Recovery", "Reflation"] else 0.02
            if self.forex_position and self.forex_entry_price and forex_price != 0:
                price_change = abs(forex_price - self.forex_entry_price) / self.forex_entry_price
                if price_change >= self.atr_multiplier * atr:
                    self.Liquidate(self.forex)
                    self.forex_position = None
                    self.forex_entry_price = None
                    self.Debug(f"Forex stop-loss triggered at price {forex_price}")
            if self.forex_position is None and abs(momentum) > self.current_params["momentum_threshold"] and vol < vol_limit and vix_momentum < 0.15 and vix_value < 50:
                signal = (sma_short > sma_long if momentum > 0 else sma_short < sma_long)
                if signal:
                    self.forex_position = "Long" if momentum > 0 else "Short"
                    self.forex_entry_price = forex_price
                    self.trade_count["Forex"] += 1
                    adjusted_forex_weight = self.AdjustWeightForBuyingPower(self.forex, self.allocations[cycle]["Forex"] * self.leverage["Forex"] * (1.0 if self.forex_position == "Long" else -1.0))
                    self.SetHoldings(self.forex, adjusted_forex_weight)
                    self.last_trade_time = self.Time
                    self.Debug(f"Forex trade executed: {self.forex_position} at price {forex_price}")
                else:
                    self.Debug(f"Forex signal not met: sma_short={sma_short}, sma_long={sma_long}, momentum={momentum}")
            else:
                self.Debug(f"Forex entry conditions not met: momentum={momentum}, vol={vol}, vix_momentum={vix_momentum}, vix_value={vix_value}")
        else:
            self.Debug("Forex data insufficient for trading")
        history = self.History([self.nvda, self.amd], self.lookback + 20, Resolution.Daily)
        nvda_price = self.Securities[self.nvda].Price if self.Securities[self.nvda].Price else (history.loc[self.nvda]["close"].iloc[-1] if not history.empty and self.nvda in history.index else 0)
        amd_price = self.Securities[self.amd].Price if self.Securities[self.amd].Price else (history.loc[self.amd]["close"].iloc[-1] if not history.empty and self.amd in history.index else 0)
        if nvda_price != 0 and amd_price != 0:
            nvda_prices = history.loc[self.nvda]["close"] if self.nvda in history.index else None
            amd_prices = history.loc[self.amd]["close"] if self.amd in history.index else None
            if nvda_prices is not None and amd_prices is not None and len(nvda_prices) >= self.lookback and len(amd_prices) >= self.lookback:
                spread, mean, std = self.CalculateSpread(nvda_prices, amd_prices, self.lookback)
                z_score = (spread - mean) / std if std != 0 else 0
                spread_vol = self.CalculateVolatility(pd.Series(spread, index=nvda_prices.index), self.lookback)
                if self.pairs_position and nvda_price != 0 and amd_price != 0:
                    self.pairs_spread_high = max(self.pairs_spread_high or abs(z_score), abs(z_score))
                    self.nvda_high = max(self.nvda_high or nvda_price, nvda_price)
                    self.amd_high = max(self.amd_high or amd_price, amd_price)
                    if abs(z_score) > 3 or abs(z_score) < self.pairs_spread_high * 0.95:
                        self.Liquidate(self.nvda)
                        self.Liquidate(self.amd)
                        self.pairs_position = None
                        self.pairs_spread_high = None
                        self.nvda_high = None
                        self.amd_high = None
                        self.Debug("Pairs trade exited: z-score condition met")
                    elif abs(z_score) < 0.05:
                        self.Liquidate(self.nvda)
                        self.Liquidate(self.amd)
                        self.pairs_position = None
                        self.pairs_spread_high = None
                        self.nvda_high = None
                        self.amd_high = None
                        self.Debug("Pairs trade exited: z-score near zero")
                    elif nvda_price < self.nvda_high * (1 - self.pairs_trailing_stop) or amd_price < self.amd_high * (1 - self.pairs_trailing_stop):
                        self.Liquidate(self.nvda)
                        self.Liquidate(self.amd)
                        self.pairs_position = None
                        self.nvda_high = None
                        self.amd_high = None
                        self.Debug("Pairs trade exited: trailing stop triggered")
                if self.pairs_position is None and abs(z_score) > self.current_params["z_score_entry"] and spread_vol < 1.5 and vix_momentum < 0.15 and vix_value < 50:
                    self.pairs_position = "LongAMDShortNVDA" if z_score > self.current_params["z_score_entry"] else "LongNVDAShortAMD"
                    self.trade_count["Pairs"] += 1
                    self.nvda_high = nvda_price
                    self.amd_high = amd_price
                    pair_weight = self.allocations[cycle]["EquityPair"] * self.leverage["EquityPair"] / 2
                    adjusted_nvda_weight = self.AdjustWeightForBuyingPower(self.nvda, pair_weight if self.pairs_position == "LongNVDAShortAMD" else -pair_weight)
                    adjusted_amd_weight = self.AdjustWeightForBuyingPower(self.amd, -pair_weight if self.pairs_position == "LongNVDAShortAMD" else pair_weight)
                    self.SetHoldings(self.nvda, adjusted_nvda_weight)
                    self.SetHoldings(self.amd, adjusted_amd_weight)
                    self.last_trade_time = self.Time
                    self.Debug(f"Pairs trade executed: {self.pairs_position}, z_score={z_score}")
                elif self.pairs_position is None:
                    self.Debug(f"Pairs entry conditions not met: z_score={z_score}, spread_vol={spread_vol}, vix_momentum={vix_momentum}, vix_value={vix_value}")
            else:
                self.Debug("Pairs data insufficient for trading")
        else:
            self.Debug("NVDA or AMD price data unavailable")
        gld_prices = self.History(self.gld, 2, Resolution.Daily)
        gld_price = self.Securities[self.gld].Price if self.Securities[self.gld].Price else (gld_prices["close"].iloc[-1] if not gld_prices.empty else 0)
        if gld_price != 0 and self.Portfolio[self.gld].Invested:
            self.gld_high = max(self.gld_high or gld_price, gld_price)
            if gld_price < self.gld_high * 0.97:
                self.gld_high = None
                self.Liquidate(self.gld)
                self.Debug("GLD position exited: trailing stop triggered")
        self.previous_cycle = cycle

    def UpdateSimulatedEquity(self, forex_data, pairs_data, current_date):
        if not self.is_training:
            return
        new_equity = 100000
        for symbol, position in self.simulated_positions.items():
            entry_price = position["entry_price"]
            weight = position["weight"]
            current_price = 0
            if symbol == self.forex:
                forex_slice = forex_data[forex_data.index.date <= current_date].tail(1)
                current_price = forex_slice["close"].iloc[-1] if not forex_slice.empty and "close" in forex_slice.columns else entry_price
            elif symbol in [self.nvda, self.amd]:
                data_slice = pairs_data[(pairs_data.index.date <= current_date) & (pairs_data['symbol'] == symbol)].tail(1)
                current_price = data_slice["close"].iloc[-1] if not data_slice.empty else entry_price
            if current_price == 0:
                continue
            price_change = (current_price - entry_price) / entry_price
            position_value = weight * self.simulated_equity * (1 + price_change)
            new_equity += position_value
        self.simulated_equity = new_equity

    def DetermineCycle(self, indicators, vix_value):
        try:
            vix = vix_value
            ief_ret = 0
            ief_prices = self.History(self.ief, 20, Resolution.Daily)
            if not ief_prices.empty and len(ief_prices) >= 20 * 24:
                ief_ret = (ief_prices["close"].iloc[-1] - ief_prices["close"].iloc[-20 * 24]) / ief_prices["close"].iloc[-20 * 24]
            if vix > 35:
                self.cycle_confirm_days = 0
                return "Stagflation"
            new_cycle = self.previous_cycle
            if ief_ret > 0 and vix < 15:
                new_cycle = "Recovery"
            elif ief_ret < 0.02 and vix > 25:
                new_cycle = "Overheat"
            elif ief_ret < 0 and vix > 30:
                new_cycle = "Stagflation"
            elif ief_ret > 0 and vix <= 20:
                new_cycle = "Reflation"
            if new_cycle == self.cycle_candidate:
                self.cycle_confirm_days += 1
                if self.cycle_confirm_days >= 5:
                    return new_cycle
            else:
                self.cycle_candidate = new_cycle
                self.cycle_confirm_days = 1
            return self.previous_cycle
        except Exception as e:
            return self.previous_cycle

    def CalculateMomentum(self, prices, period):
        if len(prices) < period:
            return 0
        return (prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]

    def CalculateSpread(self, prices1, prices2, period):
        if len(prices1) < period or len(prices2) < period:
            return 0, 0, 1
        log_spread = np.log(prices1) - np.log(prices2)
        mean = np.mean(log_spread[-period:])
        std = np.std(log_spread[-period:])
        return log_spread.iloc[-1], mean, std

    def CalculateATR(self, prices, period):
        if len(prices) < period:
            return 0.01
        high = prices.rolling(period).max()
        low = prices.rolling(period).min()
        return (high - low).mean() / prices.iloc[-1]

    def CalculateVolatility(self, prices, period):
        if len(prices) < period:
            return 0
        returns = prices.pct_change().dropna()
        return np.std(returns[-period:]) * np.sqrt(252)

    def AdjustWeightForBuyingPower(self, symbol, target_weight):
        if target_weight == 0:
            return 0
        price = self.Securities[symbol].Price
        if price == 0:
            return 0
        portfolio_value = self.Portfolio.TotalPortfolioValue
        target_value = portfolio_value * abs(target_weight)
        symbol_leverage = self.leverage.get("Forex" if symbol == self.forex else "EquityPair" if symbol in [self.nvda, self.amd] else "Bond" if symbol == self.ief else "Gold", 1.0)
        required_margin = target_value / symbol_leverage
        buying_power = self.Portfolio.MarginRemaining
        if required_margin > buying_power:
            adjusted_value = buying_power * symbol_leverage * 0.95
            adjusted_weight = adjusted_value / portfolio_value
            return adjusted_weight * (1 if target_weight > 0 else -1)
        return target_weight

    def Rebalance(self):
        if (self.Time - self.last_rebalance).days < self.rebalance_frequency:
            return
        self.last_rebalance = self.Time
        cycle = self.previous_cycle
        target = self.allocations[cycle].copy()
        vix_value = self.Securities[self.vix].Price if self.vix in self.Securities else 20
        if vix_value > 30:
            for k in ["Forex", "EquityPair"]:
                target[k] *= 0.7
        total = sum(target.values())
        for key in target:
            target[key] /= total
        if self.Securities[self.ief].Price != 0:
            weight = target["Bond"] * self.leverage["Bond"]
            adjusted_weight = self.AdjustWeightForBuyingPower(self.ief, weight)
            self.SetHoldings(self.ief, adjusted_weight)
        if self.Securities[self.gld].Price != 0:
            weight = target["Gold"] * self.leverage["Gold"]
            adjusted_weight = self.AdjustWeightForBuyingPower(self.gld, weight)
            self.SetHoldings(self.gld, adjusted_weight)
        allocation_record = {
            "Date": self.Time,
            "Forex": target["Forex"],
            "EquityPair": target["EquityPair"],
            "Bond": target["Bond"],
            "Gold": target["Gold"]
        }
        self.allocation_history = pd.concat([self.allocation_history, pd.DataFrame([allocation_record])], ignore_index=True)
        if not self.allocation_history.empty:
            csv_data = self.allocation_history.to_csv(index=False)
            self.ObjectStore.Save("Allocation_History", csv_data)
        trade_log_df = pd.DataFrame(self.trade_log)
        if not trade_log_df.empty:
            self.ObjectStore.Save("Trade_Log", trade_log_df.to_csv(index=False))
