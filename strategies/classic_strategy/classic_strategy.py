import pandas as pd
import numpy as np
import ta
from typing import Dict

class ClassicStrategy:
    
    def __init__(self):
        self.name = "Classic Strategy"
        print(f"Strategy {self.name} initialized")
        print(f"Using RSI + MACD + Bollinger + Volume + MA")

    def analyze(self, df: pd.DataFrame) -> Dict:

        #indicators calculation
        df = self._calculate_indicators(df)
        last_row = df.iloc[-1]

        # RSI strategy
        signal_rsi = self._rsi_strategy(last_row)

        #MACD Strategy
        signal_macd = self._macd_strategy(df.tail(3))

        # Bollinger Bands
        signal_bb = self._bollinger_strategy(last_row)

        # Volume
        signal_volume = self._volume_strategy(last_row)

        # Trend (Ma Crossover)
        signal_trend = self._trend_strategy(last_row)

        # Vote system
        signals = {
            'rsi': signal_rsi,
            'macd': signal_macd,
            'bollinger': signal_bb,
            'volume': signal_volume,
            'trend': signal_trend
        }

        buy_votes = sum(1 for signal in signals.values() if signal == 'BUY')
        sell_votes = sum(1 for signal in signals.values() if signal == 'SELL')

        if buy_votes >= 3:
            decision = "BUY"
            confidence = buy_votes / 5
        elif sell_votes >= 3:
            decision = "SELL"
            confidence = sell_votes / 5
        else:
            decision = "HOLD"
            confidence = 0.5

        return {
            'decision': decision,
            'confidence': confidence,
            'signals': signals,
            'strategy': 'CLASSIC',
            'metrics': {
                'rsi': float(last_row['rsi']),
                'macd': float(last_row['macd']),
                'price': float(last_row['close']),
                'volume_ratio': float(last_row['volume_ratio']),
            }
        }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Calculate all technical indicators
        df = df.copy()

        #RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

        #MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        # Moving average
        df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
        df['ema_12'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
        df['ema_26'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()

        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()

        #Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        return df

    def _rsi_strategy(self, row: pd.Series) -> str:

        # RSI < 30 = BUY, RSI > 70 = SELL
        rsi = row['rsi']
        if rsi < 30:
            return 'BUY'
        elif rsi > 70:
            return 'SELL'
        return 'HOLD'

    def _macd_strategy(self, df_tail: pd.DataFrame) -> str:
        current = df_tail.iloc[-1]
        previous = df_tail.iloc[-2]

        if (previous['macd'] <= previous['macd_signal'] and current['macd'] > current['macd']):
            return 'BUY'
        elif (previous['macd'] >= previous['macd_signal'] and current['macd'] < current['macd_signal']):
            return 'SELL'
        return 'HOLD'

    def _bollinger_strategy(self, row: pd.Series) -> str:
        price = row['close']

        if price <= row['bb_lower']:
            return 'BUY'
        elif price >= row['bb_upper']:
            return 'SELL'
        return 'HOLD'

    def _volume_strategy(self, row: pd.Series) -> str:
        if row['volume_ratio'] > 1.5:
            if row['close'] > row['sma_20']:
                return 'BUY'
            else:
                return 'SELL'
        return 'HOLD'

    def _trend_strategy(self, row: pd.Series) -> str:
        if row['ema_12'] > row['ema_26']:
            return 'BUY'
        elif row['ema_12'] < row['ema26']:
            return 'SELL'
        return 'HOLD'

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000) -> Dict:

        balance = initial_balance
        btc_holding = 0
        trades = []

        for i in range(50, len(df)):
            window = df.iloc[i-50:i]
            signal = self.analyze(window)

            current_price = df.iloc[i]['close']

            if signal['decision'] == 'BUY' and signal['confidence'] > 0.65 and balance > 0:
                amount = balance * 0.95
                btc_bought = amount / current_price
                btc_holding += btc_bought
                balance -= amount

                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'amount': btc_bought,
                    'confidence': signal['confidence']
                    })

            elif signal['decision'] == 'SELL' and signal['confidence'] > 0.65 and btc_holding > 0:
                amount = btc_holding * current_price
                balance += amount

                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'amount': btc_holding,
                    'profit': amount - initial_balance,
                    'confidence': signal['confidence']
                })

                btc_holding = 0

        final_value = balance + (btc_holding * df.iloc[-1]['close'])

        return {
            'strategy': 'CLASSIC',
            'initial_balance': initial_balance,
            'final_value': final_value,
            'profit': final_value - initial_balance,
            'profit_pct': ((final_value - initial_balance) / initial_balance) * 100,
            'trades': trades,
            'total_trades': len(trades),
            'win_rate': len([t for t in trades if t.get('profit', 0) > 0]) / len(trades) if trades else 0
        }