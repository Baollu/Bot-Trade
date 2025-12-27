"""
Nexus Trade - Multi-Crypto Training Script
Entraîne automatiquement un modèle pour chaque crypto
"""

import os
import sys
from train_model import CryptoPredictor

# Liste des cryptos à entraîner
CRYPTOS = [
    {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'days': 30},
    {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'days': 30},
    {'symbol': 'SOLUSDT', 'name': 'Solana', 'days': 30},
    {'symbol': 'ADAUSDT', 'name': 'Cardano', 'days': 30},
    {'symbol': 'DOGEUSDT', 'name': 'Dogecoin', 'days': 30},
]

def train_crypto(crypto_config):
    """
    Entraîne un modèle pour une crypto spécifique
    """
    symbol = crypto_config['symbol']
    name = crypto_config['name']
    days = crypto_config['days']
    
    print("\n" + "="*70)
    print(f"🤖 ENTRAÎNEMENT: {name} ({symbol})")
    print("="*70)
    
    try:
        # Initialisation
        predictor = CryptoPredictor(sequence_length=30, prediction_horizon=1)
        
        # Téléchargement des données
        print(f"📡 Téléchargement {days} jours de données pour {name}...")
        df = predictor.fetch_historical_data(symbol=symbol, interval='1m', days=days)
        
        if len(df) < 1000:
            print(f"⚠️ Pas assez de données pour {name} ({len(df)} points)")
            print(f"   Minimum requis: 1000 points")
            return False
        
        # Création des features
        print(f"🔧 Création des features techniques pour {name}...")
        features = predictor.create_technical_features(df)
        
        # Préparation des séquences
        print(f"📊 Préparation des séquences pour {name}...")
        X, y, feature_names = predictor.prepare_sequences(features)
        
        # Split train/val/test
        train_size = int(0.7 * len(X))
        val_size = int(0.15 * len(X))
        
        X_train = X[:train_size]
        y_train = y[:train_size]
        X_val = X[train_size:train_size + val_size]
        y_val = y[train_size:train_size + val_size]
        X_test = X[train_size + val_size:]
        y_test = y[train_size + val_size:]
        
        print(f"\n📊 Dataset split pour {name}:")
        print(f"  Train: {len(X_train)} samples")
        print(f"  Val:   {len(X_val)} samples")
        print(f"  Test:  {len(X_test)} samples")
        
        # Construction et entraînement
        print(f"\n🏗️ Construction du modèle GRU pour {name}...")
        predictor.model = predictor.build_model(
            input_shape=(predictor.sequence_length, len(feature_names))
        )
        
        print(f"🚀 Entraînement du modèle pour {name}...")
        print(f"   (Cela peut prendre 10-20 minutes...)")
        
        history = predictor.train(
            X_train, y_train,
            X_val, y_val,
            epochs=50,  # Réduit pour gagner du temps
            batch_size=64
        )
        
        # Évaluation
        print(f"\n📈 Évaluation du modèle pour {name}...")
        accuracy = predictor.evaluate(X_test, y_test)
        
        # Export ONNX avec nom spécifique
        if accuracy > 0.50:  # Seuil de qualité
            output_name = f'crypto_predictor_{symbol.lower()}.onnx'
            metadata_name = f'model_metadata_{symbol.lower()}.json'
            
            print(f"\n📦 Export ONNX pour {name}...")
            predictor.export_to_onnx(
                feature_names, 
                output_path=output_name
            )
            
            # Renommer le fichier metadata
            if os.path.exists('model_metadata.json'):
                os.rename('model_metadata.json', metadata_name)
            
            print(f"\n✅ Modèle {name} entraîné avec succès!")
            print(f"   Fichiers créés:")
            print(f"   - {output_name}")
            print(f"   - {metadata_name}")
            print(f"   Accuracy: {accuracy:.2%}")
            
            return True
        else:
            print(f"\n⚠️ Accuracy trop faible pour {name}: {accuracy:.2%}")
            print(f"   Modèle non exporté (seuil minimum: 50%)")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur lors de l'entraînement de {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Entraîne tous les modèles
    """
    print("="*70)
    print("🤖 NEXUS TRADE - ENTRAÎNEMENT MULTI-CRYPTO")
    print("="*70)
    print(f"\nNombre de cryptos à entraîner: {len(CRYPTOS)}")
    print(f"Temps estimé: {len(CRYPTOS) * 15} minutes\n")
    
    # Demander confirmation
    response = input("Voulez-vous continuer? (y/n): ")
    if response.lower() != 'y':
        print("Annulé.")
        return
    
    results = {}
    successful = 0
    failed = 0
    
    # Entraînement de chaque crypto
    for i, crypto in enumerate(CRYPTOS, 1):
        print(f"\n{'='*70}")
        print(f"Progression: {i}/{len(CRYPTOS)}")
        print(f"{'='*70}")
        
        success = train_crypto(crypto)
        results[crypto['symbol']] = success
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DE L'ENTRAÎNEMENT")
    print("="*70)
    print(f"\nTotal cryptos: {len(CRYPTOS)}")
    print(f"✅ Succès: {successful}")
    print(f"❌ Échecs: {failed}")
    print(f"📈 Taux de réussite: {successful/len(CRYPTOS)*100:.1f}%")
    
    print("\n📋 Détails par crypto:")
    for symbol, success in results.items():
        status = "✅ OK" if success else "❌ ÉCHEC"
        print(f"  {symbol:12s} : {status}")
    
    print("\n" + "="*70)
    
    if successful > 0:
        print("\n🎉 Entraînement terminé avec succès!")
        print("\nFichiers créés:")
        for crypto in CRYPTOS:
            symbol = crypto['symbol'].lower()
            if results[crypto['symbol']]:
                print(f"  - crypto_predictor_{symbol}.onnx")
                print(f"  - model_metadata_{symbol}.json")
        
        print("\n🚀 Vous pouvez maintenant lancer le système multi-crypto:")
        print("   go run cmd/main_multi_crypto.go")
    else:
        print("\n⚠️ Aucun modèle n'a pu être entraîné avec succès.")
        print("   Vérifiez votre connexion internet et réessayez.")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
