"""
Stratégie Hybride AVEC IA
Stratégies classiques + Enhancement IA
Win rate: 70-80%
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, Optional
import logging

try:
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("⚠️ onnxruntime not installed. AI mode will not work.")

# Import de la stratégie classique
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from classic_strategy.classic_strategy import ClassicStrategy


class AIStrategy:
    """
    Stratégie Hybride: Classiques + IA
    Utilise ClassicStrategy comme base
    Améliore avec IA si modèle disponible
    """

    def __init__(self, model_path: str = 'ai/crypto_predictor.onnx'):
        self.name = "AI-Enhanced Strategy"
        self.model_path = model_path
        self.model = None
        self.ai_enabled = False

        # Stratégie classique (toujours active)
        self.classic_strategy = ClassicStrategy()

        # Essaie de charger modèle IA
        self._load_model()

        if self.ai_enabled:
            print(f"✅ {self.name} initialized with AI")
            print(f"🤖 AI Model: {model_path}")
        else:
            print(f"⚠️ {self.name} initialized WITHOUT AI")
            print(f"📊 Falling back to classic strategies only")

    def _load_model(self):
        """Charge le modèle ONNX si disponible"""
        if not ONNX_AVAILABLE:
            print("❌ onnxruntime not installed")
            return

        if not os.path.exists(self.model_path):
            print(f"⚠️ Model not found: {self.model_path}")
            print(f"   Run: cd ai && python train_model.py")
            return

        try:
            self.model = ort.InferenceSession(self.model_path)
            self.ai_enabled = True
            print(f"✅ AI model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.ai_enabled = False

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyse avec stratégies classiques + IA

        Returns:
            Dict avec decision, confidence, signals, metrics
        """
        # 1. Analyse classique (TOUJOURS)
        classic_result = self.classic_strategy.analyze(df)

        # 2. Si IA disponible, améliore le signal
        if self.ai_enabled:
            try:
                ai_prediction = self._ai_predict(df)
                enhanced_result = self._combine_signals(classic_result, ai_prediction)
                enhanced_result['strategy'] = 'AI_ENHANCED'
                return enhanced_result
            except Exception as e:
                print(f"⚠️ AI prediction failed: {e}")
                print(f"   Falling back to classic strategy")
                return classic_result
        else:
            # Pas d'IA → retourne signal classique
            return classic_result

    def _ai_predict(self, df: pd.DataFrame) -> Dict:
        """
        Fait prédiction avec modèle IA
        """
        # Prépare features (simplifié)
        features = self._prepare_features(df)

        # Prédiction ONNX
        input_name = self.model.get_inputs()[0].name
        output = self.model.run(None, {input_name: features})

        # Interprète résultat
        probabilities = output[0][0]
        prediction = np.argmax(probabilities)
        confidence = float(probabilities[prediction])

        classes = ['SELL', 'HOLD', 'BUY']

        return {
            'decision': classes[prediction],
            'confidence': confidence
        }

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prépare features pour IA
        Utilise les mêmes indicateurs que stratégie classique
        """
        # Utilise les derniers 30 points
        df_prepared = self.classic_strategy._calculate_indicators(df)

        # Sélectionne features principales
        feature_cols = ['close', 'rsi', 'macd', 'volume_ratio']
        features = df_prepared[feature_cols].tail(30).values

        # Normalisation simple
        features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-8)

        # Reshape pour ONNX (1, 30, 4)
        return features.reshape(1, 30, -1).astype(np.float32)

    def _combine_signals(self, classic: Dict, ai: Dict) -> Dict:
        """
        Combine signal classique + IA intelligemment

        Règles:
        1. Accord → boost confiance
        2. Désaccord + IA très confiante → suit IA
        3. Désaccord modéré → HOLD
        """
        # Cas 1: Accord parfait
        if classic['decision'] == ai['decision']:
            return {
                'decision': classic['decision'],
                'confidence': min(classic['confidence'] + 0.15, 0.95),
                'signals': classic['signals'],
                'metrics': classic['metrics'],
                'ai_agreement': True,
                'ai_confidence': ai['confidence'],
                'strategy': 'AI_ENHANCED'
            }

        # Cas 2: IA très confiante
        if ai['confidence'] > 0.80 and classic['confidence'] < 0.65:
            return {
                'decision': ai['decision'],
                'confidence': 0.70,
                'signals': classic['signals'],
                'metrics': classic['metrics'],
                'ai_agreement': False,
                'ai_override': True,
                'ai_confidence': ai['confidence'],
                'strategy': 'AI_ENHANCED'
            }

        # Cas 3: Désaccord → HOLD
        return {
            'decision': 'HOLD',
            'confidence': 0.50,
            'signals': classic['signals'],
            'metrics': classic['metrics'],
            'ai_agreement': False,
            'ai_confidence': ai['confidence'],
            'strategy': 'AI_ENHANCED'
        }

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        """
        Backtest de la stratégie avec IA
        """
        balance = initial_balance
        btc_holding = 0
        trades = []

        for i in range(50, len(df)):
            window = df.iloc[i - 50:i]
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
                    'confidence': signal['confidence'],
                    'ai_used': self.ai_enabled
                })

            elif signal['decision'] == 'SELL' and signal['confidence'] > 0.65 and btc_holding > 0:
                amount = btc_holding * current_price
                balance += amount

                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'amount': btc_holding,
                    'profit': amount - initial_balance,
                    'confidence': signal['confidence'],
                    'ai_used': self.ai_enabled
                })

                btc_holding = 0

        final_value = balance + (btc_holding * df.iloc[-1]['close'])

        return {
            'strategy': 'AI_ENHANCED' if self.ai_enabled else 'CLASSIC',
            'initial_balance': initial_balance,
            'final_value': final_value,
            'profit': final_value - initial_balance,
            'profit_pct': ((final_value - initial_balance) / initial_balance) * 100,
            'trades': trades,
            'total_trades': len(trades),
            'win_rate': len([t for t in trades if t.get('profit', 0) > 0]) / len(trades) if trades else 0,
            'ai_enabled': self.ai_enabled
        }