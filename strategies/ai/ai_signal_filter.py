"""
Algorithme: XGBoost (meilleur que LSTM pour ce use case)
Source: "Machine Learning for Asset Managers" (Marcos Lopez de Prado, 2020)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

try:
    from xgboost import XGBClassifier
    import joblib
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("⚠️ xgboost not installed. AI filtering disabled.")

from classic_strategy.proven_strategies import ProvenStrategies


class AISignalFilter:
    def __init__(self, model_path: Optional[str] = 'ai/signal_filter.pkl'):
        self.name = "AI Signal Filter & Enhancer"
        self.model_path = model_path
        self.model = None
        self.ai_enabled = False

        self.proven_strategies = ProvenStrategies()

        self._load_model()

        if self.ai_enabled:
            print(f"✅ {self.name} initialized WITH AI")
            print(f"🤖 Model: {model_path}")
        else:
            print(f"⚠️ {self.name} initialized WITHOUT AI")
            print(f"📊 Using proven strategies only")

    def _load_model(self):
        if not XGBOOST_AVAILABLE:
            return

        try:
            import os
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.ai_enabled = True
                print(f"✅ AI filter model loaded")
            else:
                print(f"⚠️ Model not found: {self.model_path}")
                print(f"   Train with: python train_signal_filter.py")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.ai_enabled = False

    def analyze(self, df: pd.DataFrame) -> Dict:
        classic_signal = self.proven_strategies.analyze(df)

        if self.ai_enabled:
            try:
                ai_filtered = self._filter_signal(df, classic_signal)
                return ai_filtered
            except Exception as e:
                print(f"⚠️ AI filtering failed: {e}")
                print(f"   Falling back to proven strategies")
                return classic_signal
        else:
            return classic_signal

    def _filter_signal(self, df: pd.DataFrame, classic_signal: Dict) -> Dict:
        features = self._prepare_features(df, classic_signal)

        signal_quality = self.model.predict_proba(features)[0]

        prob_good = signal_quality[1]

        if classic_signal['decision'] == 'BUY':
            if prob_good > 0.70:  # IA confirme fortement
                return {
                    **classic_signal,
                    'decision': 'BUY',
                    'confidence': min(classic_signal['confidence'] * 1.3, 0.95),
                    'ai_filter': 'CONFIRMED_STRONG',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN'
                }
            elif prob_good > 0.55:  # IA confirme modérément
                return {
                    **classic_signal,
                    'decision': 'BUY',
                    'confidence': classic_signal['confidence'] * 1.1,
                    'ai_filter': 'CONFIRMED',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN'
                }
            else:
                return {
                    **classic_signal,
                    'decision': 'HOLD',
                    'confidence': 0.5,
                    'ai_filter': 'REJECTED',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN',
                    'reasons': classic_signal['reasons'] + ["IA: Signal filtré (probabilité faible)"]
                }

        elif classic_signal['decision'] == 'SELL':
            if prob_good > 0.70:
                return {
                    **classic_signal,
                    'decision': 'SELL',
                    'confidence': min(classic_signal['confidence'] * 1.3, 0.95),
                    'ai_filter': 'CONFIRMED_STRONG',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN'
                }
            elif prob_good > 0.55:
                return {
                    **classic_signal,
                    'decision': 'SELL',
                    'confidence': classic_signal['confidence'] * 1.1,
                    'ai_filter': 'CONFIRMED',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN'
                }
            else:
                return {
                    **classic_signal,
                    'decision': 'HOLD',
                    'confidence': 0.5,
                    'ai_filter': 'REJECTED',
                    'ai_confidence': prob_good,
                    'strategy': 'AI_FILTERED_PROVEN',
                    'reasons': classic_signal['reasons'] + ["IA: Signal filtré (probabilité faible)"]
                }

        else:
            return {
                **classic_signal,
                'ai_filter': 'NEUTRAL',
                'ai_confidence': prob_good,
                'strategy': 'AI_FILTERED_PROVEN'
            }

    def _prepare_features(self, df: pd.DataFrame, classic_signal: Dict) -> np.ndarray:
        last = df.iloc[-1]

        signals = classic_signal['signals']

        feature_vector = []

        for strategy_name in ['bollinger_mean_reversion', 'rsi_divergence',
                             'macd_histogram', 'vwap', 'ema_crossover']:
            sig = signals[strategy_name]
            # One-hot encoding: [is_buy, is_sell, is_hold]
            feature_vector.append(1 if sig['decision'] == 'BUY' else 0)
            feature_vector.append(1 if sig['decision'] == 'SELL' else 0)
            feature_vector.append(sig['confidence'])

        metrics = classic_signal['metrics']
        feature_vector.extend([
            metrics['rsi'] / 100,  # Normalisé 0-1
            metrics['macd_histogram'],
            metrics['distance_from_vwap'],
            metrics['bollinger_position'],
            last['volume'] / df['volume'].rolling(20).mean().iloc[-1] if len(df) >= 20 else 1.0,
            last['atr'] / last['close'] if 'atr' in last else 0.02,
            (last['ema_12'] - last['ema_26']) / last['close'] if 'ema_12' in last else 0,
            df['close'].pct_change().iloc[-1],
            df['close'].pct_change().iloc[-2] if len(df) >= 2 else 0,
            df['close'].pct_change().iloc[-3] if len(df) >= 3 else 0,
        ])

        feature_vector.append(classic_signal['confidence'])

        return np.array(feature_vector).reshape(1, -1)

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        balance = initial_balance
        crypto_holding = 0
        trades = []

        for i in range(100, len(df)):
            window = df.iloc[max(0, i-200):i]
            signal = self.analyze(window)

            current_price = df.iloc[i]['close']

            confidence_threshold = 0.65 if self.ai_enabled else 0.60

            if signal['decision'] == 'BUY' and signal['confidence'] > confidence_threshold and balance > 0:
                amount = balance * 0.95
                crypto_bought = amount / current_price
                crypto_holding += crypto_bought
                balance -= amount

                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'amount': crypto_bought,
                    'confidence': signal['confidence'],
                    'ai_filter': signal.get('ai_filter', 'N/A'),
                    'reasons': signal.get('reasons', [])
                })

            elif signal['decision'] == 'SELL' and signal['confidence'] > confidence_threshold and crypto_holding > 0:
                amount = crypto_holding * current_price
                balance += amount
                profit = amount - (trades[-1]['price'] * trades[-1]['amount']) if trades else 0

                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'amount': crypto_holding,
                    'profit': profit,
                    'confidence': signal['confidence'],
                    'ai_filter': signal.get('ai_filter', 'N/A'),
                    'reasons': signal.get('reasons', [])
                })

                crypto_holding = 0

        final_value = balance + (crypto_holding * df.iloc[-1]['close'])

        return {
            'strategy': 'AI_FILTERED_PROVEN' if self.ai_enabled else 'PROVEN_PROFESSIONAL',
            'initial_balance': initial_balance,
            'final_value': final_value,
            'profit': final_value - initial_balance,
            'profit_pct': ((final_value - initial_balance) / initial_balance) * 100,
            'trades': trades,
            'total_trades': len(trades),
            'win_rate': len([t for t in trades if t.get('profit', 0) > 0]) / len([t for t in trades if 'profit' in t]) if trades else 0,
            'ai_enabled': self.ai_enabled
        }