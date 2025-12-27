"""
Nexus Trade - AI Training Module
Entraîne un modèle GRU optimisé pour la prédiction de prix Bitcoin
Basé sur les dernières recherches (2024-2025) : GRU > LSTM pour crypto
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import tf2onnx
import onnx
import requests
import json
from datetime import datetime, timedelta
import ta  # Technical Analysis library
import warnings
warnings.filterwarnings('ignore')


class CryptoPredictor:
    """
    Modèle GRU optimisé pour prédire les mouvements de prix crypto
    Architecture basée sur: https://peerj.com/articles/cs-2675/
    """
    
    def __init__(self, sequence_length=30, prediction_horizon=1):
        """
        Args:
            sequence_length: Nombre de minutes d'historique (30 minutes recommandé)
            prediction_horizon: Minutes à prédire (1 minute pour ce projet)
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.scaler_price = MinMaxScaler()
        self.scaler_features = MinMaxScaler()
        self.model = None
        
    def fetch_historical_data(self, symbol='BTCUSDT', interval='1m', days=7):
        """
        Récupère les données historiques depuis Binance
        """
        print(f"📡 Téléchargement des données {symbol} ({days} jours)...")
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        url = 'https://api.binance.com/api/v3/klines'
        all_data = []
        
        while start_time < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
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
        
        # Conversion des types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        
        print(f"✅ {len(df)} points de données téléchargés")
        return df
    
    def create_technical_features(self, df):
        """
        Crée des features techniques avancées basées sur la recherche
        Features démontrées efficaces: RSI, MACD, Bollinger, ATR, momentum
        """
        print("🔧 Création des features techniques...")
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['close'] = close
        features['returns'] = close.pct_change()
        features['log_returns'] = np.log(close / close.shift(1))
        
        # Volatility (critical pour crypto)
        features['volatility'] = close.rolling(window=20).std()
        features['close_off_high'] = (high - close) / high
        
        # RSI - Relative Strength Index
        features['rsi_14'] = ta.momentum.RSIIndicator(close, window=14).rsi()
        features['rsi_7'] = ta.momentum.RSIIndicator(close, window=7).rsi()
        
        # MACD - Moving Average Convergence Divergence
        macd = ta.trend.MACD(close)
        features['macd'] = macd.macd()
        features['macd_signal'] = macd.macd_signal()
        features['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(close)
        features['bb_high'] = bollinger.bollinger_hband()
        features['bb_low'] = bollinger.bollinger_lband()
        features['bb_mid'] = bollinger.bollinger_mavg()
        features['bb_width'] = (features['bb_high'] - features['bb_low']) / features['bb_mid']
        
        # ATR - Average True Range (volatilité)
        features['atr'] = ta.volatility.AverageTrueRange(high, low, close).average_true_range()
        
        # Moving Averages
        features['sma_20'] = ta.trend.SMAIndicator(close, window=20).sma_indicator()
        features['ema_12'] = ta.trend.EMAIndicator(close, window=12).ema_indicator()
        features['ema_26'] = ta.trend.EMAIndicator(close, window=26).ema_indicator()
        
        # Momentum indicators
        features['momentum_10'] = close - close.shift(10)
        features['rate_of_change'] = ta.momentum.ROCIndicator(close).roc()
        
        # Volume indicators
        features['volume'] = volume
        features['volume_sma'] = volume.rolling(window=20).mean()
        features['volume_ratio'] = volume / features['volume_sma']
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(high, low, close)
        features['stoch_k'] = stoch.stoch()
        features['stoch_d'] = stoch.stoch_signal()
        
        # On-Balance Volume
        features['obv'] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        
        # Target: mouvement du prix dans les prochaines minutes
        features['price_change'] = close.shift(-self.prediction_horizon) - close
        features['price_change_pct'] = (close.shift(-self.prediction_horizon) - close) / close * 100
        
        # Classification: Hausse/Baisse > 1%
        features['target'] = 0  # Neutre
        features.loc[features['price_change_pct'] > 1.0, 'target'] = 1  # Hausse
        features.loc[features['price_change_pct'] < -1.0, 'target'] = 2  # Baisse
        
        # Supprime les NaN
        features = features.dropna()
        
        print(f"✅ {len(features.columns)} features créées, {len(features)} samples valides")
        return features
    
    def prepare_sequences(self, features):
        """
        Prépare les séquences pour le GRU
        Format: [samples, time_steps, features]
        """
        print("📊 Préparation des séquences...")
        
        # Sépare features et target
        target_cols = ['price_change', 'price_change_pct', 'target']
        feature_cols = [col for col in features.columns if col not in target_cols]
        
        X = features[feature_cols].values
        y = features['target'].values
        
        # Normalisation
        X_scaled = self.scaler_features.fit_transform(X)
        
        # Création des séquences
        X_sequences = []
        y_sequences = []
        
        for i in range(len(X_scaled) - self.sequence_length):
            X_sequences.append(X_scaled[i:i + self.sequence_length])
            y_sequences.append(y[i + self.sequence_length])
        
        X_sequences = np.array(X_sequences)
        y_sequences = np.array(y_sequences)
        
        print(f"✅ Séquences créées: {X_sequences.shape}")
        return X_sequences, y_sequences, feature_cols
    
    def build_model(self, input_shape, num_classes=3):
        """
        Architecture GRU optimisée basée sur les meilleures pratiques 2024
        GRU est plus rapide que LSTM avec des performances similaires
        """
        print("🏗️ Construction du modèle GRU...")
        
        model = Sequential([
            # Première couche GRU
            GRU(128, return_sequences=True, input_shape=input_shape),
            BatchNormalization(),
            Dropout(0.3),
            
            # Deuxième couche GRU
            GRU(64, return_sequences=True),
            BatchNormalization(),
            Dropout(0.3),
            
            # Troisième couche GRU
            GRU(32, return_sequences=False),
            BatchNormalization(),
            Dropout(0.2),
            
            # Couches denses
            Dense(64, activation='relu'),
            Dropout(0.2),
            Dense(32, activation='relu'),
            
            # Output layer
            Dense(num_classes, activation='softmax')
        ])
        
        optimizer = Adam(learning_rate=0.001)
        model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print(model.summary())
        return model
    
    def train(self, X_train, y_train, X_val, y_val, epochs=100, batch_size=32):
        """
        Entraîne le modèle avec early stopping et learning rate scheduling
        """
        print("🚀 Début de l'entraînement...")
        
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            ),
            ModelCheckpoint(
                'best_model.h5',
                monitor='val_accuracy',
                save_best_only=True,
                verbose=1
            )
        ]
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def export_to_onnx(self, feature_names, output_path='crypto_predictor.onnx'):
        """
        Exporte le modèle en format ONNX pour utilisation avec Go
        ONNX permet une inférence ultra-rapide (<100ms requis)
        """
        print("📦 Export vers ONNX...")
        
        # Spécification de l'input
        spec = (tf.TensorSpec(
            (None, self.sequence_length, len(feature_names)), 
            tf.float32, 
            name="input"
        ),)
        
        # Conversion
        onnx_model, _ = tf2onnx.convert.from_keras(
            self.model,
            input_signature=spec,
            opset=13,
            output_path=output_path
        )
        
        # Sauvegarde des metadata
        metadata = {
            'sequence_length': self.sequence_length,
            'features': feature_names,
            'classes': ['NEUTRAL', 'UP', 'DOWN'],
            'scaler_mean': self.scaler_features.mean_.tolist(),
            'scaler_scale': self.scaler_features.scale_.tolist(),
            'created_at': datetime.now().isoformat(),
            'model_type': 'GRU',
            'version': '1.0'
        }
        
        with open('model_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Modèle exporté: {output_path}")
        print(f"✅ Métadonnées sauvegardées: model_metadata.json")
        
    def evaluate(self, X_test, y_test):
        """
        Évalue les performances du modèle
        """
        print("📈 Évaluation du modèle...")
        
        loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0)
        predictions = self.model.predict(X_test, verbose=0)
        predicted_classes = np.argmax(predictions, axis=1)
        
        # Calcul de la précision par classe
        from sklearn.metrics import classification_report, confusion_matrix
        
        print("\n" + "="*60)
        print("RÉSULTATS D'ÉVALUATION")
        print("="*60)
        print(f"Loss: {loss:.4f}")
        print(f"Accuracy: {accuracy:.4f}")
        print("\nClassification Report:")
        print(classification_report(
            y_test, 
            predicted_classes,
            target_names=['NEUTRAL', 'UP (>1%)', 'DOWN (<-1%)']
        ))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, predicted_classes))
        print("="*60)
        
        return accuracy


def main():
    """
    Pipeline complet d'entraînement
    """
    print("="*60)
    print("🤖 NEXUS TRADE - AI TRAINING PIPELINE")
    print("="*60)
    
    # 1. Initialisation
    predictor = CryptoPredictor(sequence_length=30, prediction_horizon=1)
    
    # 2. Téléchargement des données
    df = predictor.fetch_historical_data(symbol='BTCUSDT', interval='1m', days=30)
    
    # 3. Création des features
    features = predictor.create_technical_features(df)
    
    # 4. Préparation des séquences
    X, y, feature_names = predictor.prepare_sequences(features)
    
    # 5. Split train/val/test
    train_size = int(0.7 * len(X))
    val_size = int(0.15 * len(X))
    
    X_train = X[:train_size]
    y_train = y[:train_size]
    X_val = X[train_size:train_size + val_size]
    y_val = y[train_size:train_size + val_size]
    X_test = X[train_size + val_size:]
    y_test = y[train_size + val_size:]
    
    print(f"\n📊 Dataset split:")
    print(f"  Train: {len(X_train)} samples")
    print(f"  Val:   {len(X_val)} samples")
    print(f"  Test:  {len(X_test)} samples")
    
    # 6. Construction et entraînement
    predictor.model = predictor.build_model(
        input_shape=(predictor.sequence_length, len(feature_names))
    )
    
    history = predictor.train(
        X_train, y_train,
        X_val, y_val,
        epochs=100,
        batch_size=64
    )
    
    # 7. Évaluation
    accuracy = predictor.evaluate(X_test, y_test)
    
    # 8. Export ONNX
    if accuracy > 0.55:  # Seuil minimum de qualité
        predictor.export_to_onnx(feature_names)
        print("\n✅ Modèle prêt pour la production!")
    else:
        print(f"\n⚠️ Accuracy trop faible ({accuracy:.2%}). Réentraînement recommandé.")
    
    print("\n" + "="*60)
    print("✅ ENTRAÎNEMENT TERMINÉ")
    print("="*60)


if __name__ == '__main__':
    main()
