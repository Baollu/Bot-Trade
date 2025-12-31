"""
ENTRAÎNEMENT DU FILTRE IA
Apprend quand les signaux des stratégies classiques fonctionnent

Approche:
- Utilise XGBoost (meilleur que LSTM pour ce cas)
- Entraîne sur données historiques Bitcoin
- Target: "Ce signal a-t-il fonctionné ?"

Basé sur: "Machine Learning for Asset Managers" (Lopez de Prado, 2020)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
import joblib
import requests
from datetime import datetime, timedelta
import sys
sys.path.append('..')

from classic_strategy.proven_strategies import ProvenStrategies


class SignalFilterTrainer:
    """
    Entraîne un modèle XGBoost pour filtrer les signaux
    """
    
    def __init__(self):
        self.proven_strategies = ProvenStrategies()
        self.model = None
    
    def fetch_historical_data(self, symbol='BTCUSDT', days=90):
        """
        Télécharge données historiques Binance
        """
        print(f"📡 Téléchargement {days} jours de données {symbol}...")
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        url = 'https://api.binance.com/api/v3/klines'
        all_data = []
        
        while start_time < end_time:
            params = {
                'symbol': symbol,
                'interval': '1h',  # 1 heure (meilleur pour ce use case)
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if not data:
                break
            
            all_data.extend(data)
            start_time = data[-1][0] + 1
        
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        
        print(f"✅ {len(df)} points téléchargés")
        return df
    
    def create_training_dataset(self, df: pd.DataFrame):
        """
        Crée dataset d'entraînement
        
        Pour chaque signal des stratégies classiques:
        - Features: Les signaux + contexte marché
        - Label: Le signal a-t-il fonctionné ? (prix après > prix avant)
        """
        print("🔧 Création du dataset d'entraînement...")
        
        X_data = []
        y_data = []
        
        # Pour chaque point (sauf les 100 premiers et 10 derniers)
        for i in range(100, len(df) - 10):
            # Fenêtre pour analyse
            window = df.iloc[max(0, i-200):i]
            
            # Signal des stratégies
            signal = self.proven_strategies.analyze(window)
            
            # Skip HOLD signals (on veut apprendre sur BUY/SELL)
            if signal['decision'] == 'HOLD':
                continue
            
            # Prépare features
            features = self._extract_features(window, signal)
            
            # Label: Le trade a-t-il été profitable ?
            current_price = df.iloc[i]['close']
            future_price = df.iloc[i+10]['close']  # 10 périodes après
            
            if signal['decision'] == 'BUY':
                # Profitable si prix monte
                label = 1 if future_price > current_price * 1.01 else 0
            else:  # SELL
                # Profitable si prix baisse
                label = 1 if future_price < current_price * 0.99 else 0
            
            X_data.append(features)
            y_data.append(label)
        
        X = np.array(X_data)
        y = np.array(y_data)
        
        print(f"✅ Dataset créé: {len(X)} samples")
        print(f"   Positive samples: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
        print(f"   Negative samples: {len(y)-y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")
        
        return X, y
    
    def _extract_features(self, df: pd.DataFrame, signal: dict) -> np.ndarray:
        """
        Extrait features pour l'IA (même fonction que dans ai_signal_filter.py)
        """
        last = df.iloc[-1]
        
        signals = signal['signals']
        feature_vector = []
        
        # 1. Signaux des 5 stratégies
        for strategy_name in ['bollinger_mean_reversion', 'rsi_divergence', 
                             'macd_histogram', 'vwap', 'ema_crossover']:
            sig = signals[strategy_name]
            feature_vector.append(1 if sig['decision'] == 'BUY' else 0)
            feature_vector.append(1 if sig['decision'] == 'SELL' else 0)
            feature_vector.append(sig['confidence'])
        
        # 2. Contexte marché
        metrics = signal['metrics']
        feature_vector.extend([
            metrics['rsi'] / 100,
            metrics['macd_histogram'],
            metrics['distance_from_vwap'],
            metrics['bollinger_position'],
            last['volume'] / df['volume'].rolling(20).mean().iloc[-1] if len(df) >= 20 else 1.0,
            last.get('atr', 0) / last['close'] if last.get('atr', 0) > 0 else 0.02,
            (last.get('ema_12', 0) - last.get('ema_26', 0)) / last['close'] if last.get('ema_12', 0) > 0 else 0,
            df['close'].pct_change().iloc[-1],
            df['close'].pct_change().iloc[-2] if len(df) >= 2 else 0,
            df['close'].pct_change().iloc[-3] if len(df) >= 3 else 0,
        ])
        
        # 3. Confiance globale
        feature_vector.append(signal['confidence'])
        
        return np.array(feature_vector)
    
    def train(self, X, y):
        """
        Entraîne le modèle XGBoost
        """
        print("\n🚀 Entraînement du modèle XGBoost...")
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Modèle XGBoost optimisé pour trading
        # Compatible XGBoost 2.x
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=20,  # Déplacé ici pour XGBoost 2.x
            eval_metric='logloss'
        )

        # Entraînement (compatible XGBoost 2.x)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # Évaluation
        print("\n📈 RÉSULTATS:")

        # Train accuracy
        train_pred = self.model.predict(X_train)
        train_acc = (train_pred == y_train).mean()
        print(f"Train Accuracy: {train_acc:.2%}")

        # Test accuracy
        test_pred = self.model.predict(X_test)
        test_acc = (test_pred == y_test).mean()
        print(f"Test Accuracy:  {test_acc:.2%}")

        # AUC Score
        test_proba = self.model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, test_proba)
        print(f"AUC Score:      {auc:.3f}")

        # Classification report
        print("\nClassification Report (Test):")
        print(classification_report(y_test, test_pred,
                                   target_names=['Bad Signal', 'Good Signal']))

        # Feature importance
        print("\n🔍 Top 10 Features Importantes:")
        feature_importance = self.model.feature_importances_
        top_features = np.argsort(feature_importance)[-10:][::-1]
        for i, idx in enumerate(top_features, 1):
            print(f"  {i}. Feature {idx}: {feature_importance[idx]:.3f}")

        return test_acc, auc

    def save_model(self, path='signal_filter.pkl'):
        """Sauvegarde le modèle"""
        joblib.dump(self.model, path)
        print(f"\n✅ Modèle sauvegardé: {path}")

    def cross_validate(self, X, y):
        """Cross-validation pour vérifier robustesse"""
        print("\n🔄 Cross-validation (5-fold)...")

        # Crée un modèle sans early_stopping pour CV (incompatible avec cross_val_score)
        cv_model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            random_state=42,
            n_jobs=-1,
            # PAS de early_stopping_rounds pour CV
        )

        scores = cross_val_score(cv_model, X, y, cv=5, scoring='accuracy')
        print(f"CV Scores: {scores}")
        print(f"Mean CV Accuracy: {scores.mean():.2%} (+/- {scores.std()*2:.2%})")


def main():
    """
    Pipeline complet d'entraînement
    """
    print("="*70)
    print("🤖 ENTRAÎNEMENT DU FILTRE IA")
    print("="*70)
    print("\nApproche: Signal Validation (Renaissance Technologies style)")
    print("Algorithme: XGBoost")
    print()

    # 1. Initialisation
    trainer = SignalFilterTrainer()

    # 2. Téléchargement données
    df = trainer.fetch_historical_data(symbol='BTCUSDT', days=90)

    # 3. Création dataset
    X, y = trainer.create_training_dataset(df)

    if len(X) < 100:
        print("\n❌ Pas assez de données pour entraînement")
        return

    # 4. Entraînement
    test_acc, auc = trainer.train(X, y)

    # 5. Cross-validation (optionnelle)
    try:
        trainer.cross_validate(X, y)
    except Exception as e:
        print(f"\n⚠️ Cross-validation échouée (pas grave): {e}")
        print("   Le modèle principal est déjà entraîné et évalué ✅")

    # 6. Sauvegarde
    if test_acc > 0.55:  # Seuil minimum
        trainer.save_model('signal_filter.pkl')

        print("\n" + "="*70)
        print("✅ ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
        print("="*70)
        print(f"\nPerformance:")
        print(f"  Test Accuracy: {test_acc:.2%}")
        print(f"  AUC Score:     {auc:.3f}")
        print(f"\nLe modèle est prêt à être utilisé !")
        print(f"\nAttention: Accuracy > 55% est déjà EXCELLENT pour trading")
        print(f"(Accuracy 60% = potentiel de profit énorme)")
    else:
        print("\n⚠️ Accuracy trop faible. Collectez plus de données ou ajustez paramètres.")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()