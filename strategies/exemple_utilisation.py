#!/usr/bin/env python3
"""
🚀 EXEMPLE D'UTILISATION DU SYSTÈME DE TRADING
"""

from ai.ai_signal_filter import AISignalFilter
import pandas as pd
import numpy as np
from datetime import datetime


def main():
    print("=" * 70)
    print("🤖 SYSTÈME DE TRADING - DÉMO")
    print("=" * 70)

    # 1. Crée des données synthétiques (remplace par tes vraies données Bitcoin)
    print("\n📊 Création des données de test...")
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    df = pd.DataFrame({
        'close': np.random.randn(200).cumsum() + 50000,
        'high': np.random.randn(200).cumsum() + 50100,
        'low': np.random.randn(200).cumsum() + 49900,
        'volume': np.random.rand(200) * 1000000
    }, index=dates)

    print(f"✅ {len(df)} points de données créés")
    print(f"   Période: {df.index[0]} → {df.index[-1]}")
    print(f"   Prix: ${df['close'].iloc[-1]:,.2f}")

    # 2. Analyse avec stratégies + IA
    print("\n🔍 Analyse en cours...")
    strategy = AISignalFilter(model_path='ai/signal_filter.pkl')
    result = strategy.analyze(df)

    # 3. Affiche les résultats
    print("\n" + "=" * 70)
    print("🎯 RÉSULTATS DE L'ANALYSE")
    print("=" * 70)

    print(f"\n💰 Prix actuel: ${result['metrics']['price']:,.2f}")
    print(f"\n📈 DÉCISION: {result['decision']}")
    print(f"🎲 Confiance: {result['confidence']:.0%}")

    if 'ai_filter' in result:
        print(f"\n🤖 FILTRE IA:")
        print(f"   Status: {result['ai_filter']}")
        print(f"   Confiance IA: {result.get('ai_confidence', 0):.0%}")

    print(f"\n📊 RAISONS ({len(result['reasons'])}):")
    for i, reason in enumerate(result['reasons'], 1):
        print(f"   {i}. {reason}")

    # 4. Recommandations
    print("\n" + "=" * 70)
    print("💡 RECOMMANDATIONS")
    print("=" * 70)

    if result['decision'] == 'BUY':
        print("\n✅ SIGNAL D'ACHAT")
        print("   📌 Actions recommandées:")
        print("   1. Vérifie le volume (doit être élevé)")
        print("   2. Place un stop-loss à -2% du prix actuel")
        print("   3. Target: +3% (ratio 1.5:1)")
        print("   4. Taille position: MAX 2% du capital")

    elif result['decision'] == 'SELL':
        print("\n⚠️ SIGNAL DE VENTE")
        print("   📌 Actions recommandées:")
        print("   1. Ferme les positions longues")
        print("   2. Considère un short si expérimenté")
        print("   3. Protège ton capital")

    else:  # HOLD
        print("\n⏸️ PAS DE SIGNAL CLAIR")
        print("   📌 Actions recommandées:")
        print("   1. Reste en dehors du marché")
        print("   2. Attends un signal plus fort")
        print("   3. Patience = capital préservé")

    print("\n" + "=" * 70)
    print("⚠️  RAPPEL IMPORTANT")
    print("=" * 70)
    print("   • Ceci est une DÉMO avec données synthétiques")
    print("   • TOUJOURS backtester avant de trader réel")
    print("   • JAMAIS trader avec argent que tu ne peux pas perdre")
    print("   • MAX 2% du capital par trade")
    print("   • TOUJOURS utiliser stop-loss")
    print("=" * 70)


if __name__ == "__main__":
    main()