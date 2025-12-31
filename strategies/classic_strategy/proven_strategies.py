import pandas as pd
import numpy as np
import ta
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Signal:
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    reason: str  # Pourquoi ce signal


class ProvenStrategies:

    def __init__(self):
        self.name = "Proven Professional Strategies"
        print(f"✅ {self.name} initialized")
        print("📚 Sources: Wilder, Bollinger, Appel, Turtle Traders, Market Makers")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        df = self._calculate_indicators(df)
        
        # Les 5 stratégies prouvées
        signal_bollinger = self._bollinger_mean_reversion(df)
        signal_rsi_div = self._rsi_divergence(df)
        signal_macd_hist = self._macd_histogram(df)
        signal_vwap = self._vwap_strategy(df)
        signal_ema_crossover = self._ema_crossover(df)
        
        signals = {
            'bollinger_mean_reversion': signal_bollinger,
            'rsi_divergence': signal_rsi_div,
            'macd_histogram': signal_macd_hist,
            'vwap': signal_vwap,
            'ema_crossover': signal_ema_crossover
        }
        
        weights = {
            'bollinger_mean_reversion': 1.2,  # Très fiable selon Bollinger
            'rsi_divergence': 1.5,             # Très forte selon Wilder
            'macd_histogram': 1.0,
            'vwap': 1.3,                       # Utilisé par institutions
            'ema_crossover': 0.8               # Bon pour trends, moins pour range
        }
        
        buy_score = sum(weights[k] for k, v in signals.items() if v.decision == 'BUY')
        sell_score = sum(weights[k] for k, v in signals.items() if v.decision == 'SELL')
        total_weight = sum(weights.values())
        
        if buy_score > sell_score and buy_score / total_weight > 0.5:
            decision = 'BUY'
            confidence = buy_score / total_weight
            reasons = [v.reason for k, v in signals.items() if v.decision == 'BUY']
        elif sell_score > buy_score and sell_score / total_weight > 0.5:
            decision = 'SELL'
            confidence = sell_score / total_weight
            reasons = [v.reason for k, v in signals.items() if v.decision == 'SELL']
        else:
            decision = 'HOLD'
            confidence = 0.5
            reasons = ["Pas de consensus clair entre les stratégies"]
        
        last_row = df.iloc[-1]
        
        return {
            'decision': decision,
            'confidence': confidence,
            'reasons': reasons,
            'signals': {k: {'decision': v.decision, 'confidence': v.confidence, 'reason': v.reason} 
                       for k, v in signals.items()},
            'strategy': 'PROVEN_PROFESSIONAL',
            'metrics': {
                'price': float(last_row['close']),
                'rsi': float(last_row['rsi']),
                'macd_histogram': float(last_row['macd_histogram']),
                'distance_from_vwap': float((last_row['close'] - last_row['vwap']) / last_row['vwap'] * 100),
                'bollinger_position': float((last_row['close'] - last_row['bb_lower']) / 
                                           (last_row['bb_upper'] - last_row['bb_lower']))
            }
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        
        df['ema_12'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
        df['ema_26'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def _bollinger_mean_reversion(self, df: pd.DataFrame) -> Signal:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        bb_position = (last['close'] - last['bb_lower']) / (last['bb_upper'] - last['bb_lower'])
        
        if bb_position < 0.1 and last['rsi'] < 35:
            return Signal(
                decision='BUY',
                confidence=0.75,
                reason="Bollinger: Prix oversold + RSI<35 (mean reversion probable)"
            )
        
        elif bb_position > 0.9 and last['rsi'] > 65:
            return Signal(
                decision='SELL',
                confidence=0.75,
                reason="Bollinger: Prix overbought + RSI>65 (mean reversion probable)"
            )
        
        return Signal('HOLD', 0.5, "Bollinger: Prix dans range normal")
    
    def _rsi_divergence(self, df: pd.DataFrame) -> Signal:
        if len(df) < 10:
            return Signal('HOLD', 0.5, "RSI: Pas assez de données")
        
        recent = df.tail(10)
        
        price_lows = recent['low'].values
        rsi_lows = recent['rsi'].values
        
        if price_lows[-1] < price_lows[-5] < price_lows[-10]:
            if rsi_lows[-1] > rsi_lows[-5] > rsi_lows[-10]:
                if recent.iloc[-1]['rsi'] < 40:
                    return Signal(
                        decision='BUY',
                        confidence=0.85,
                        reason="RSI: Divergence bullish détectée (très fort signal)"
                    )

        price_highs = recent['high'].values
        rsi_highs = recent['rsi'].values
        
        if price_highs[-1] > price_highs[-5] > price_highs[-10]:
            if rsi_highs[-1] < rsi_highs[-5] < rsi_highs[-10]:
                if recent.iloc[-1]['rsi'] > 60:
                    return Signal(
                        decision='SELL',
                        confidence=0.85,
                        reason="RSI: Divergence bearish détectée (très fort signal)"
                    )
        
        last_rsi = recent.iloc[-1]['rsi']
        if last_rsi < 30:
            return Signal('BUY', 0.65, "RSI: Oversold classique (< 30)")
        elif last_rsi > 70:
            return Signal('SELL', 0.65, "RSI: Overbought classique (> 70)")
        
        return Signal('HOLD', 0.5, "RSI: Pas de divergence ni extreme")
    
    def _macd_histogram(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal('HOLD', 0.5, "MACD: Pas assez de données")
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['macd_histogram'] <= 0 and last['macd_histogram'] > 0:
            if abs(last['macd_histogram']) > abs(prev['macd_histogram']):
                return Signal(
                    decision='BUY',
                    confidence=0.70,
                    reason="MACD: Crossover bullish + histogram expansion"
                )
        
        elif prev['macd_histogram'] >= 0 and last['macd_histogram'] < 0:
            if abs(last['macd_histogram']) > abs(prev['macd_histogram']):
                return Signal(
                    decision='SELL',
                    confidence=0.70,
                    reason="MACD: Crossover bearish + histogram expansion"
                )
        
        return Signal('HOLD', 0.5, "MACD: Pas de crossover")
    
    def _vwap_strategy(self, df: pd.DataFrame) -> Signal:
        last = df.iloc[-1]
        
        distance = (last['close'] - last['vwap']) / last['vwap'] * 100
        
        high_volume = last['volume'] > last['volume_sma'] * 1.2
        
        if distance < -0.5 and high_volume:
            return Signal(
                decision='BUY',
                confidence=0.80,
                reason=f"VWAP: Prix {distance:.1f}% sous VWAP + volume élevé (institutions achètent)"
            )
        
        elif distance > 0.5 and high_volume:
            return Signal(
                decision='SELL',
                confidence=0.80,
                reason=f"VWAP: Prix {distance:.1f}% sur VWAP + volume élevé (institutions vendent)"
            )
        
        return Signal('HOLD', 0.5, "VWAP: Prix proche de VWAP ou volume faible")
    
    def _ema_crossover(self, df: pd.DataFrame) -> Signal:
        if len(df) < 3:
            return Signal('HOLD', 0.5, "EMA: Pas assez de données")
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['ema_12'] <= prev['ema_26'] and last['ema_12'] > last['ema_26']:
            if last['close'] > last['ema_50']:
                return Signal(
                    decision='BUY',
                    confidence=0.65,
                    reason="EMA: Golden cross confirmé (trend bullish)"
                )
        
        elif prev['ema_12'] >= prev['ema_26'] and last['ema_12'] < last['ema_26']:
            if last['close'] < last['ema_50']:
                return Signal(
                    decision='SELL',
                    confidence=0.65,
                    reason="EMA: Death cross confirmé (trend bearish)"
                )
        
        if last['ema_12'] > last['ema_26'] and last['close'] > last['ema_50']:
            return Signal('BUY', 0.55, "EMA: Trend bullish établi")
        elif last['ema_12'] < last['ema_26'] and last['close'] < last['ema_50']:
            return Signal('SELL', 0.55, "EMA: Trend bearish établi")
        
        return Signal('HOLD', 0.5, "EMA: Pas de trend clair")
    
    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        balance = initial_balance
        crypto_holding = 0
        trades = []
        
        for i in range(50, len(df)):
            window = df.iloc[max(0, i-100):i]
            signal = self.analyze(window)
            
            current_price = df.iloc[i]['close']
            
            if signal['decision'] == 'BUY' and signal['confidence'] > 0.60 and balance > 0:
                amount = balance * 0.95
                crypto_bought = amount / current_price
                crypto_holding += crypto_bought
                balance -= amount
                
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'amount': crypto_bought,
                    'confidence': signal['confidence'],
                    'reasons': signal['reasons']
                })
            
            elif signal['decision'] == 'SELL' and signal['confidence'] > 0.60 and crypto_holding > 0:
                amount = crypto_holding * current_price
                balance += amount
                profit = amount - initial_balance if len(trades) % 2 == 0 else 0
                
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'amount': crypto_holding,
                    'profit': profit,
                    'confidence': signal['confidence'],
                    'reasons': signal['reasons']
                })
                
                crypto_holding = 0
        
        final_value = balance + (crypto_holding * df.iloc[-1]['close'])
        
        return {
            'strategy': 'PROVEN_PROFESSIONAL',
            'initial_balance': initial_balance,
            'final_value': final_value,
            'profit': final_value - initial_balance,
            'profit_pct': ((final_value - initial_balance) / initial_balance) * 100,
            'trades': trades,
            'total_trades': len(trades),
            'win_rate': len([t for t in trades if t.get('profit', 0) > 0]) / len([t for t in trades if 'profit' in t]) if trades else 0
        }
