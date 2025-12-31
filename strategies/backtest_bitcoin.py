#!/usr/bin/env python3
"""
📊 BACKTEST AVEC VRAIES DONNÉES BITCOIN
Télécharge les données depuis Binance et lance un backtest complet
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from ai.ai_signal_filter import AISignalFilter
from classic_strategy.proven_strategies import ProvenStrategies


def download_bitcoin_data(days=365):
    """
    Télécharge les données Bitcoin depuis Binance
    """
    print(f"\n📡 Téléchargement des données Bitcoin ({days} jours)...")

    # Calcule les timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)

    # API Binance
    url = "https://api.binance.com/api/v3/klines"

    all_data = []
    current_start = start_ts

    while current_start < end_ts:
        params = {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'startTime': current_start,
            'endTime': end_ts,
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if not data:
                break

            all_data.extend(data)
            current_start = data[-1][0] + 1

            print(f"   Téléchargé: {len(all_data)} points...", end='\r')

        except Exception as e:
            print(f"\n❌ Erreur téléchargement: {e}")
            break

    # Convertit en DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    # Nettoie et convertit
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = df[['open', 'high', 'low', 'close', 'volume']]

    print(f"\n✅ {len(df)} points téléchargés")
    print(f"   Période: {df.index[0]} → {df.index[-1]}")
    print(f"   Prix début: ${df['close'].iloc[0]:,.2f}")
    print(f"   Prix fin: ${df['close'].iloc[-1]:,.2f}")

    return df


def backtest_comparison(df, initial_balance=10000):
    """
    Compare stratégies classiques vs avec IA
    """
    print("\n" + "=" * 70)
    print("🔬 BACKTEST COMPARATIF")
    print("=" * 70)

    # 1. Stratégies classiques seules
    print("\n📊 Test 1: Stratégies Classiques (sans IA)")
    classic = ProvenStrategies()
    results_classic = classic.backtest(df, initial_balance=initial_balance)

    print(f"\n💰 Capital initial: ${results_classic['initial_balance']:,.2f}")
    print(f"💵 Capital final: ${results_classic['final_value']:,.2f}")
    print(f"📈 Profit: ${results_classic['profit']:,.2f} ({results_classic['profit_pct']:.2f}%)")
    print(f"📊 Trades: {results_classic['total_trades']}")

    # Calcule winning/losing trades depuis la liste
    winning_trades = len([t for t in results_classic['trades'] if t.get('profit', 0) > 0])
    losing_trades = len([t for t in results_classic['trades'] if t.get('profit', 0) < 0])

    print(f"✅ Gagnants: {winning_trades}")
    print(f"❌ Perdants: {losing_trades}")
    print(f"🎯 Win Rate: {results_classic['win_rate']:.0%}")

    # Calcule max drawdown
    max_dd = 0
    peak = results_classic['initial_balance']
    for i, trade in enumerate(results_classic['trades']):
        if trade['type'] == 'SELL':
            current_value = results_classic['initial_balance'] + trade.get('profit', 0)
            if current_value > peak:
                peak = current_value
            dd = (peak - current_value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

    print(f"💸 Drawdown Max: {max_dd:.2%}")

    # 2. Avec filtre IA
    print("\n" + "-" * 70)
    print("🤖 Test 2: Stratégies + Filtre IA")

    try:
        ai_strategy = AISignalFilter(model_path='ai/signal_filter.pkl')
        results_ai = ai_strategy.backtest(df, initial_balance=initial_balance)

        print(f"\n💰 Capital initial: ${results_ai['initial_balance']:,.2f}")
        print(f"💵 Capital final: ${results_ai['final_value']:,.2f}")
        print(f"📈 Profit: ${results_ai['profit']:,.2f} ({results_ai['profit_pct']:.2f}%)")
        print(f"📊 Trades: {results_ai['total_trades']}")

        # Calcule winning/losing trades
        winning_trades_ai = len([t for t in results_ai['trades'] if t.get('profit', 0) > 0])
        losing_trades_ai = len([t for t in results_ai['trades'] if t.get('profit', 0) < 0])

        print(f"✅ Gagnants: {winning_trades_ai}")
        print(f"❌ Perdants: {losing_trades_ai}")
        print(f"🎯 Win Rate: {results_ai['win_rate']:.0%}")

        # Calcule max drawdown
        max_dd_ai = 0
        peak_ai = results_ai['initial_balance']
        for trade in results_ai['trades']:
            if trade['type'] == 'SELL':
                current_value = results_ai['initial_balance'] + trade.get('profit', 0)
                if current_value > peak_ai:
                    peak_ai = current_value
                dd = (peak_ai - current_value) / peak_ai if peak_ai > 0 else 0
                max_dd_ai = max(max_dd_ai, dd)

        print(f"💸 Drawdown Max: {max_dd_ai:.2%}")

        # Comparaison
        print("\n" + "=" * 70)
        print("📊 COMPARAISON")
        print("=" * 70)

        profit_diff = results_ai['profit'] - results_classic['profit']
        winrate_diff = results_ai['win_rate'] - results_classic['win_rate']
        trades_diff = results_ai['total_trades'] - results_classic['total_trades']

        print(f"\n💰 Différence de profit: ${profit_diff:+,.2f}")
        print(f"🎯 Amélioration win rate: {winrate_diff:+.1%}")
        print(f"📊 Différence trades: {trades_diff:+d}")

        if profit_diff > 0:
            improvement_pct = (profit_diff / abs(results_classic['profit'])) * 100 if results_classic[
                                                                                          'profit'] != 0 else 0
            print(f"\n✅ L'IA améliore les résultats de {improvement_pct:.1f}%")
        else:
            print(f"\n⚠️ L'IA réduit le profit (plus conservateur)")

    except FileNotFoundError:
        print("\n⚠️ Modèle IA non trouvé (signal_filter.pkl)")
        print("   Lance d'abord: cd ai && python train_signal_filter.py")

    # 3. Buy & Hold (référence)
    print("\n" + "-" * 70)
    print("📌 Test 3: Buy & Hold (référence)")

    buy_hold_profit = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * initial_balance
    buy_hold_pct = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100

    print(f"\n💰 Capital initial: ${initial_balance:,.2f}")
    print(f"💵 Capital final: ${initial_balance + buy_hold_profit:,.2f}")
    print(f"📈 Profit: ${buy_hold_profit:,.2f} ({buy_hold_pct:.2f}%)")

    print("\n" + "=" * 70)
    print("🏆 CONCLUSION")
    print("=" * 70)

    strategies = {
        'Buy & Hold': buy_hold_profit,
        'Stratégies Classiques': results_classic['profit']
    }

    try:
        strategies['Stratégies + IA'] = results_ai['profit']
    except:
        pass

    best = max(strategies, key=strategies.get)
    print(f"\n🥇 Meilleure stratégie: {best}")
    print(f"   Profit: ${strategies[best]:,.2f}")

    return results_classic


def main():
    print("=" * 70)
    print("🤖 BACKTEST BITCOIN - SYSTÈME COMPLET")
    print("=" * 70)

    # Choix de la période
    print("\n📅 Choisir la période:")
    print("   1. 30 jours (rapide)")
    print("   2. 90 jours (recommandé)")
    print("   3. 180 jours")
    print("   4. 365 jours (1 an)")

    choice = input("\nTon choix (1-4) [défaut: 2]: ").strip()

    days_map = {'1': 30, '2': 90, '3': 180, '4': 365}
    days = days_map.get(choice, 90)

    # Télécharge les données
    df = download_bitcoin_data(days=days)

    # Sauvegarde les données
    filename = f'bitcoin_data_{days}days.csv'
    df.to_csv(filename)
    print(f"\n💾 Données sauvegardées: {filename}")

    # Lance le backtest
    backtest_comparison(df)

    print("\n" + "=" * 70)
    print("✅ BACKTEST TERMINÉ")
    print("=" * 70)
    print(f"\n📁 Données disponibles: {filename}")
    print("   Tu peux les réutiliser pour d'autres tests")


if __name__ == "__main__":
    main()