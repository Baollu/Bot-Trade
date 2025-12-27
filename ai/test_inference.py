"""
Nexus Trade - ONNX Inference Test
Teste l'inférence du modèle ONNX pour vérifier la latence (<100ms requis)
"""

import onnxruntime as ort
import numpy as np
import json
import time
from redis import Redis
import ta
import pandas as pd


class ONNXPredictor:
    """
    Prédicteur utilisant le modèle ONNX exporté
    Optimisé pour des inférences ultra-rapides
    """
    
    def __init__(self, model_path='crypto_predictor.onnx', metadata_path='model_metadata.json'):
        """
        Charge le modèle ONNX et ses métadonnées
        """
        print("🔄 Chargement du modèle ONNX...")
        
        # Chargement du modèle ONNX
        self.session = ort.InferenceSession(
            model_path,
            providers=['CPUExecutionProvider']
        )
        
        # Chargement des métadonnées
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        self.sequence_length = self.metadata['sequence_length']
        self.features = self.metadata['features']
        self.scaler_mean = np.array(self.metadata['scaler_mean'])
        self.scaler_scale = np.array(self.metadata['scaler_scale'])
        self.classes = self.metadata['classes']
        
        print(f"✅ Modèle chargé: {self.metadata['model_type']} v{self.metadata['version']}")
        print(f"   Séquence: {self.sequence_length} minutes")
        print(f"   Features: {len(self.features)}")
        print(f"   Classes: {self.classes}")
    
    def extract_features(self, df):
        """
        Extrait les features d'un DataFrame de prix
        """
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        features_dict = {}
        
        # Price features
        features_dict['close'] = close.iloc[-1]
        features_dict['returns'] = close.pct_change().iloc[-1] if len(close) > 1 else 0.0
        features_dict['log_returns'] = np.log(close.iloc[-1] / close.iloc[-2]) if len(close) > 1 else 0.0
        
        # Volatility
        features_dict['volatility'] = close.rolling(window=min(20, len(close))).std().iloc[-1]
        features_dict['close_off_high'] = ((high.iloc[-1] - close.iloc[-1]) / high.iloc[-1]) if high.iloc[-1] != 0 else 0.0
        
        # RSI
        features_dict['rsi_14'] = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1] if len(close) >= 14 else 50.0
        features_dict['rsi_7'] = ta.momentum.RSIIndicator(close, window=7).rsi().iloc[-1] if len(close) >= 7 else 50.0
        
        # MACD
        if len(close) >= 26:
            macd = ta.trend.MACD(close)
            features_dict['macd'] = macd.macd().iloc[-1]
            features_dict['macd_signal'] = macd.macd_signal().iloc[-1]
            features_dict['macd_diff'] = macd.macd_diff().iloc[-1]
        else:
            features_dict['macd'] = features_dict['macd_signal'] = features_dict['macd_diff'] = 0.0
        
        # Bollinger Bands
        if len(close) >= 20:
            bollinger = ta.volatility.BollingerBands(close)
            bb_high = bollinger.bollinger_hband().iloc[-1]
            bb_low = bollinger.bollinger_lband().iloc[-1]
            bb_mid = bollinger.bollinger_mavg().iloc[-1]
            features_dict['bb_high'] = bb_high
            features_dict['bb_low'] = bb_low
            features_dict['bb_mid'] = bb_mid
            features_dict['bb_width'] = (bb_high - bb_low) / bb_mid if bb_mid != 0 else 0
        else:
            features_dict['bb_high'] = features_dict['bb_low'] = features_dict['bb_mid'] = close.iloc[-1]
            features_dict['bb_width'] = 0.0
        
        # ATR
        features_dict['atr'] = ta.volatility.AverageTrueRange(high, low, close).average_true_range().iloc[-1] if len(close) >= 14 else 0.0
        
        # Moving Averages
        features_dict['sma_20'] = ta.trend.SMAIndicator(close, window=20).sma_indicator().iloc[-1] if len(close) >= 20 else close.iloc[-1]
        features_dict['ema_12'] = ta.trend.EMAIndicator(close, window=12).ema_indicator().iloc[-1] if len(close) >= 12 else close.iloc[-1]
        features_dict['ema_26'] = ta.trend.EMAIndicator(close, window=26).ema_indicator().iloc[-1] if len(close) >= 26 else close.iloc[-1]
        
        # Momentum
        if len(close) >= 10:
            features_dict['momentum_10'] = close.iloc[-1] - close.iloc[-11]
            features_dict['rate_of_change'] = ta.momentum.ROCIndicator(close).roc().iloc[-1]
        else:
            features_dict['momentum_10'] = features_dict['rate_of_change'] = 0.0
        
        # Volume
        features_dict['volume'] = volume.iloc[-1]
        volume_sma = volume.rolling(window=min(20, len(volume))).mean().iloc[-1]
        features_dict['volume_sma'] = volume_sma
        features_dict['volume_ratio'] = volume.iloc[-1] / volume_sma if volume_sma != 0 else 1.0
        
        # Stochastic
        if len(close) >= 14:
            stoch = ta.momentum.StochasticOscillator(high, low, close)
            features_dict['stoch_k'] = stoch.stoch().iloc[-1]
            features_dict['stoch_d'] = stoch.stoch_signal().iloc[-1]
        else:
            features_dict['stoch_k'] = features_dict['stoch_d'] = 50.0
        
        # OBV
        features_dict['obv'] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume().iloc[-1]
        
        # Retourne dans l'ordre des features du modèle
        return np.array([features_dict.get(feat, 0.0) for feat in self.features])
    
    def predict(self, prices_data):
        """
        Fait une prédiction à partir des données de prix récentes
        
        Args:
            prices_data: Liste de dicts avec {open, high, low, close, volume}
        
        Returns:
            dict avec {class, probabilities, confidence, latency}
        """
        start_time = time.time()
        
        # Conversion en DataFrame
        df = pd.DataFrame(prices_data)
        
        # Extraction des features pour chaque point de temps
        features_sequence = []
        for i in range(len(df) - self.sequence_length + 1, len(df) + 1):
            df_slice = df.iloc[:i]
            features_sequence.append(self.extract_features(df_slice))
        
        # Normalisation
        features_array = np.array(features_sequence)
        features_normalized = (features_array - self.scaler_mean) / self.scaler_scale
        
        # Reshape pour ONNX: (1, sequence_length, num_features)
        input_data = features_normalized.reshape(1, self.sequence_length, -1).astype(np.float32)
        
        # Inférence
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        
        predictions = self.session.run([output_name], {input_name: input_data})[0]
        
        # Résultats
        predicted_class = int(np.argmax(predictions[0]))
        probabilities = predictions[0].tolist()
        confidence = float(max(probabilities))
        
        latency = (time.time() - start_time) * 1000  # en ms
        
        return {
            'class': self.classes[predicted_class],
            'class_id': predicted_class,
            'probabilities': {
                'NEUTRAL': probabilities[0],
                'UP': probabilities[1],
                'DOWN': probabilities[2]
            },
            'confidence': confidence,
            'latency_ms': latency
        }


def test_with_redis():
    """
    Test d'inférence en récupérant les données depuis Redis
    """
    print("\n" + "="*60)
    print("🧪 TEST D'INFÉRENCE AVEC REDIS")
    print("="*60)
    
    # Connexion à Redis
    redis_client = Redis(host='localhost', port=6379, decode_responses=True)
    
    # Chargement du modèle
    predictor = ONNXPredictor()
    
    print("\n📊 Récupération des données depuis Redis...")
    
    # Récupération des derniers prix
    prices = redis_client.lrange('market_data:btcusdt', -predictor.sequence_length, -1)
    
    if len(prices) < predictor.sequence_length:
        print(f"❌ Pas assez de données: {len(prices)}/{predictor.sequence_length}")
        return
    
    # Conversion en format attendu
    prices_data = []
    for p in prices:
        price = float(p)
        prices_data.append({
            'open': price,
            'high': price * 1.001,
            'low': price * 0.999,
            'close': price,
            'volume': 1000.0
        })
    
    # Prédiction
    result = predictor.predict(prices_data)
    
    print("\n" + "="*60)
    print("📈 RÉSULTAT DE PRÉDICTION")
    print("="*60)
    print(f"Classe prédite: {result['class']}")
    print(f"Confiance: {result['confidence']:.2%}")
    print(f"\nProbabilités:")
    for cls, prob in result['probabilities'].items():
        print(f"  {cls:8s}: {prob:.2%}")
    print(f"\n⏱️  Latence: {result['latency_ms']:.2f} ms")
    
    if result['latency_ms'] < 100:
        print("✅ Latence < 100ms: OBJECTIF ATTEINT!")
    else:
        print("⚠️ Latence > 100ms: OPTIMISATION REQUISE")
    
    print("="*60)


def test_with_synthetic_data():
    """
    Test d'inférence avec des données synthétiques
    """
    print("\n" + "="*60)
    print("🧪 TEST D'INFÉRENCE AVEC DONNÉES SYNTHÉTIQUES")
    print("="*60)
    
    predictor = ONNXPredictor()
    
    # Génération de données synthétiques
    base_price = 50000.0
    prices_data = []
    
    for i in range(predictor.sequence_length):
        price = base_price + np.random.randn() * 100
        prices_data.append({
            'open': price,
            'high': price + abs(np.random.randn() * 50),
            'low': price - abs(np.random.randn() * 50),
            'close': price,
            'volume': 1000 + abs(np.random.randn() * 500)
        })
    
    # Test de plusieurs prédictions pour mesurer la latence moyenne
    latencies = []
    for _ in range(10):
        result = predictor.predict(prices_data)
        latencies.append(result['latency_ms'])
    
    print(f"\n📊 Statistiques de latence (10 prédictions):")
    print(f"  Moyenne: {np.mean(latencies):.2f} ms")
    print(f"  Min:     {np.min(latencies):.2f} ms")
    print(f"  Max:     {np.max(latencies):.2f} ms")
    print(f"  Std:     {np.std(latencies):.2f} ms")
    
    if np.mean(latencies) < 100:
        print("\n✅ Latence moyenne < 100ms: OBJECTIF ATTEINT!")
    else:
        print("\n⚠️ Latence moyenne > 100ms: OPTIMISATION REQUISE")


if __name__ == '__main__':
    # Test avec données synthétiques
    test_with_synthetic_data()
    
    # Test avec Redis (nécessite que Redis soit en cours d'exécution)
    try:
        test_with_redis()
    except Exception as e:
        print(f"\n⚠️ Impossible de se connecter à Redis: {e}")
        print("   Assurez-vous que Redis est démarré et contient des données")
