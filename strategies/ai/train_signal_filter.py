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
    def __init__(self):
        self.proven_strategies = ProvenStrategies()
        self.model = None
    
    def fetch_historical_data(self, symbol='BTCUSDT', days=90):
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        url = 'https://api.binance.com/api/v3/klines'
        all_data = []
        
        while start_time < end_time:
            params = {
                'symbol': symbol,
                'interval': '1h',
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
        X_data = []
        y_data = []
        
        for i in range(100, len(df) - 10):
            window = df.iloc[max(0, i-200):i]
            
            signal = self.proven_strategies.analyze(window)
            
            if signal['decision'] == 'HOLD':
                continue
            
            features = self._extract_features(window, signal)
            
            current_price = df.iloc[i]['close']
            future_price = df.iloc[i+10]['close']  # 10 périodes après
            
            if signal['decision'] == 'BUY':
                label = 1 if future_price > current_price * 1.01 else 0
            else:
                label = 1 if future_price < current_price * 0.99 else 0
            
            X_data.append(features)
            y_data.append(label)
        
        X = np.array(X_data)
        y = np.array(y_data)
        return X, y
    
    def _extract_features(self, df: pd.DataFrame, signal: dict) -> np.ndarray:
        last = df.iloc[-1]
        
        signals = signal['signals']
        feature_vector = []
        
        for strategy_name in ['bollinger_mean_reversion', 'rsi_divergence',
                             'macd_histogram', 'vwap', 'ema_crossover']:
            sig = signals[strategy_name]
            feature_vector.append(1 if sig['decision'] == 'BUY' else 0)
            feature_vector.append(1 if sig['decision'] == 'SELL' else 0)
            feature_vector.append(sig['confidence'])
        
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
        
        feature_vector.append(signal['confidence'])
        
        return np.array(feature_vector)
    
    def train(self, X, y):

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=20,
            eval_metric='logloss'
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        print("\n📈 result:")

        train_pred = self.model.predict(X_train)
        train_acc = (train_pred == y_train).mean()
        print(f"Train Accuracy: {train_acc:.2%}")

        test_pred = self.model.predict(X_test)
        test_acc = (test_pred == y_test).mean()
        print(f"Test Accuracy:  {test_acc:.2%}")

        test_proba = self.model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, test_proba)
        print(f"AUC Score:      {auc:.3f}")

        feature_importance = self.model.feature_importances_
        top_features = np.argsort(feature_importance)[-10:][::-1]
        for i, idx in enumerate(top_features, 1):
            print(f"  {i}. Feature {idx}: {feature_importance[idx]:.3f}")

        return test_acc, auc

    def save_model(self, path='signal_filter.pkl'):
        joblib.dump(self.model, path)
        print(f"\n✅ Model save: {path}")

    def cross_validate(self, X, y):
        print("\n🔄 Cross-validation (5-fold)...")

        cv_model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            random_state=42,
            n_jobs=-1,
        )

        scores = cross_val_score(cv_model, X, y, cv=5, scoring='accuracy')
        print(f"CV Scores: {scores}")
        print(f"Mean CV Accuracy: {scores.mean():.2%} (+/- {scores.std()*2:.2%})")


def main():
    trainer = SignalFilterTrainer()
    df = trainer.fetch_historical_data(symbol='BTCUSDT', days=90)
    X, y = trainer.create_training_dataset(df)

    if len(X) < 100:
        print("\n❌ Not enough data")
        return

    test_acc, auc = trainer.train(X, y)

    try:
        trainer.cross_validate(X, y)
    except Exception as e:
        print(f"\n⚠️ Cross-validation failed: {e}")

    if test_acc > 0.55:  # Seuil minimum
        trainer.save_model('signal_filter.pkl')

        print("\n" + "="*70)
        print("✅ Train sucess")
        print("="*70)
        print(f"\nPerformance:")
        print(f"  Test Accuracy: {test_acc:.2%}")
        print(f"  AUC Score:     {auc:.3f}")
        print(f"\nModel ready to use")
    else:
        print("\n⚠️ Accuracy too low.")

if __name__ == '__main__':
    main()