#!/usr/bin/env python3
"""
🔴 TRADING EN TEMPS RÉEL (SIMULATION)
Récupère les données Bitcoin en live et analyse toutes les heures
⚠️ ATTENTION: Mode SIMULATION - Aucun trade réel !
"""

import requests
import pandas as pd
import time
from datetime import datetime
from ai.ai_signal_filter import AISignalFilter


def get_current_bitcoin_data(lookback_hours=200):
    """
    Récupère les données Bitcoin récentes
    """
    url = "https://api.binance.com/api/v3/klines"

    params = {
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'limit': lookback_hours
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    return df[['open', 'high', 'low', 'close', 'volume']]


def analyze_and_display(strategy, df):
    """
    Analyse et affiche les résultats
    """
    result = strategy.analyze(df)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header
    print("\n" + "=" * 70)
    print(f"⏰ {current_time}")
    print("=" * 70)

    # Prix actuel
    current_price = result['metrics']['price']
    print(f"\n💰 Bitcoin: ${current_price:,.2f}")

    # Décision
    decision_emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '🟡'
    }

    emoji = decision_emoji.get(result['decision'], '⚪')
    print(f"\n{emoji} DÉCISION: {result['decision']}")
    print(f"🎲 Confiance: {result['confidence']:.0%}")

    # Filtre IA
    if 'ai_filter' in result:
        ai_emoji = '✅' if result['ai_filter'] == 'APPROVED' else '❌' if result['ai_filter'] == 'REJECTED' else '⚠️'
        print(f"\n🤖 Filtre IA: {ai_emoji} {result['ai_filter']}")
        print(f"   Confiance IA: {result.get('ai_confidence', 0):.0%}")

    # Raisons
    print(f"\n📊 Raisons ({len(result['reasons'])}):")
    for reason in result['reasons'][:5]:  # Max 5 raisons
        print(f"   • {reason}")

    # Action recommandée
    print("\n💡 Action:")
    if result['decision'] == 'BUY' and result['confidence'] > 0.65:
        print("   ✅ Signal d'achat fort - Position possible")
        print(f"   📌 Stop-loss: ${current_price * 0.98:,.2f} (-2%)")
        print(f"   📌 Target: ${current_price * 1.03:,.2f} (+3%)")
    elif result['decision'] == 'SELL' and result['confidence'] > 0.65:
        print("   ⚠️ Signal de vente - Fermer positions")
    else:
        print("   ⏸️ Pas de signal clair - Rester à l'écart")

    print("\n" + "-" * 70)


def live_monitoring(check_interval_minutes=60):
    """
    Monitoring en temps réel (boucle infinie)
    """
    print("=" * 70)
    print("🔴 MONITORING EN TEMPS RÉEL - SIMULATION")
    print("=" * 70)
    print("\n⚠️  MODE SIMULATION - Aucun trade réel")
    print(f"🔄 Vérification toutes les {check_interval_minutes} minutes")
    print("\n💡 Appuie sur Ctrl+C pour arrêter\n")

    # Charge la stratégie
    try:
        strategy = AISignalFilter(model_path='ai/signal_filter.pkl')
        print("✅ Stratégie IA chargée")
    except FileNotFoundError:
        print("⚠️ Modèle IA non trouvé, utilisation stratégies classiques")
        from classic_strategy.proven_strategies import ProvenStrategies
        strategy = ProvenStrategies()

    iteration = 0

    try:
        while True:
            iteration += 1

            try:
                # Récupère les données
                df = get_current_bitcoin_data()

                # Analyse
                analyze_and_display(strategy, df)

                # Attend
                if iteration == 1:
                    print(f"\n⏳ Prochaine analyse dans {check_interval_minutes} minutes...")
                else:
                    print(f"\n⏳ Analyse #{iteration + 1} dans {check_interval_minutes} minutes...")

                time.sleep(check_interval_minutes * 60)

            except requests.exceptions.RequestException as e:
                print(f"\n❌ Erreur réseau: {e}")
                print("⏳ Nouvelle tentative dans 5 minutes...")
                time.sleep(300)

            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                print("⏳ Nouvelle tentative dans 5 minutes...")
                time.sleep(300)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("⏹️  MONITORING ARRÊTÉ")
        print("=" * 70)
        print(f"\n📊 Total d'analyses: {iteration}")
        print("\n✅ Arrêt propre du système")


def main():
    print("=" * 70)
    print("🚀 TRADING EN TEMPS RÉEL - OPTIONS")
    print("=" * 70)

    print("\n1. 📸 Analyse UNIQUE (maintenant)")
    print("2. 🔄 Monitoring CONTINU (toutes les heures)")
    print("3. ⚡ Monitoring RAPIDE (toutes les 5 min - pour tests)")

    choice = input("\nTon choix (1-3) [défaut: 1]: ").strip()

    if choice == '2':
        live_monitoring(check_interval_minutes=60)
    elif choice == '3':
        print("\n⚠️  Mode rapide - Pour tests uniquement")
        print("   En production, utilise 1h minimum")
        input("\nAppuie sur Enter pour continuer...")
        live_monitoring(check_interval_minutes=5)
    else:
        # Analyse unique
        print("\n📡 Récupération des données...")

        try:
            strategy = AISignalFilter(model_path='ai/signal_filter.pkl')
            print("✅ Stratégie IA chargée")
        except FileNotFoundError:
            print("⚠️ Modèle IA non trouvé, utilisation stratégies classiques")
            from classic_strategy.proven_strategies import ProvenStrategies
            strategy = ProvenStrategies()

        df = get_current_bitcoin_data()
        analyze_and_display(strategy, df)

        print("\n💡 Pour monitoring continu, relance avec option 2")


if __name__ == "__main__":
    main()