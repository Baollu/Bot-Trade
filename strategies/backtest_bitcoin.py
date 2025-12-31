#!/usr/bin/env python3

import requests
import pandas as pd
from datetime import datetime, timedelta
from ai.ai_signal_filter import AISignalFilter
from classic_strategy.proven_strategies import ProvenStrategies


def download_bitcoin_data(days=365):
    print(f"\n📡 Download data Bitcoin ({days} jours)...")

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)

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

            print(f"   Download: {len(all_data)} points...", end='\r')

        except Exception as e:
            print(f"\n Error to download: {e}")
            break

    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = df[['open', 'high', 'low', 'close', 'volume']]

    print(f"\n✅ {len(df)} points download")
    print(f"   Période: {df.index[0]} → {df.index[-1]}")
    print(f"   Prix debut: ${df['close'].iloc[0]:,.2f}")
    print(f"   Prix fin: ${df['close'].iloc[-1]:,.2f}")

    return df


def backtest_comparison(df, initial_balance=10000):
    print("🔬 BACKTEST COMPARE")

    print("\n📊 Test 1: Strategies Classic (without IA)")
    classic = ProvenStrategies()
    results_classic = classic.backtest(df, initial_balance=initial_balance)

    print(f"\n💰 Capital init: ${results_classic['initial_balance']:,.2f}")
    print(f"💵 Capital final: ${results_classic['final_value']:,.2f}")
    print(f"📈 Profit: ${results_classic['profit']:,.2f} ({results_classic['profit_pct']:.2f}%)")
    print(f"📊 Trades: {results_classic['total_trades']}")

    winning_trades = len([t for t in results_classic['trades'] if t.get('profit', 0) > 0])
    losing_trades = len([t for t in results_classic['trades'] if t.get('profit', 0) < 0])

    print(f"✅ win: {winning_trades}")
    print(f" Lose: {losing_trades}")
    print(f"🎯 Win Rate: {results_classic['win_rate']:.0%}")

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

    print("🤖 Test 2: Stratégies + IA")

    try:
        ai_strategy = AISignalFilter(model_path='ai/signal_filter.pkl')
        results_ai = ai_strategy.backtest(df, initial_balance=initial_balance)

        print(f"\n💰 Capital init: ${results_ai['initial_balance']:,.2f}")
        print(f"💵 Capital final: ${results_ai['final_value']:,.2f}")
        print(f"📈 Profit: ${results_ai['profit']:,.2f} ({results_ai['profit_pct']:.2f}%)")
        print(f"📊 Trades: {results_ai['total_trades']}")

        winning_trades_ai = len([t for t in results_ai['trades'] if t.get('profit', 0) > 0])
        losing_trades_ai = len([t for t in results_ai['trades'] if t.get('profit', 0) < 0])

        print(f"✅ Win: {winning_trades_ai}")
        print(f" Lose: {losing_trades_ai}")
        print(f"🎯 Win Rate: {results_ai['win_rate']:.0%}")

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

        print("📊 COMPARAISON")

        profit_diff = results_ai['profit'] - results_classic['profit']
        winrate_diff = results_ai['win_rate'] - results_classic['win_rate']
        trades_diff = results_ai['total_trades'] - results_classic['total_trades']

        print(f"\n💰 Difference profit: ${profit_diff:+,.2f}")
        print(f"🎯 Update win rate: {winrate_diff:+.1%}")
        print(f"📊 Différence trades: {trades_diff:+d}")

        if profit_diff > 0:
            improvement_pct = (profit_diff / abs(results_classic['profit'])) * 100 if results_classic[
                                                                                          'profit'] != 0 else 0
            print(f"\n✅ L'IA upgrade result of {improvement_pct:.1f}%")
        else:
            print(f"\n⚠️ L'IA reduce profit")

    except FileNotFoundError:
        print("\n⚠️ Model IA not found (signal_filter.pkl)")
        print("   Launch first: train_signal_filter.py")

    print("📌 Test 3: Buy & Hold (reference)")

    buy_hold_profit = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * initial_balance
    buy_hold_pct = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100

    print(f"\n💰 Capital init: ${initial_balance:,.2f}")
    print(f"💵 Capital final: ${initial_balance + buy_hold_profit:,.2f}")
    print(f"📈 Profit: ${buy_hold_profit:,.2f} ({buy_hold_pct:.2f}%)")

    print("🏆 CONCLUSION")

    strategies = {
        'Buy & Hold': buy_hold_profit,
        'Stratégies Classiques': results_classic['profit']
    }

    try:
        strategies['Stratégies + IA'] = results_ai['profit']
    except:
        pass

    best = max(strategies, key=strategies.get)
    print(f"\n🥇 Best strategie: {best}")
    print(f"   Profit: ${strategies[best]:,.2f}")

    return results_classic


def main():
    print("🤖 BACKTEST BITCOIN - SYSTEM COMPLETE")

    # Choix de la période
    print("\n📅 Choisir la période:")
    print("   1. 30 days (fast)")
    print("   2. 90 days (recommended)")
    print("   3. 180 days")
    print("   4. 365 days (1 year)")

    choice = input("\nYour choice (1-4): ").strip()

    days_map = {'1': 30, '2': 90, '3': 180, '4': 365}
    days = days_map.get(choice, 90)

    df = download_bitcoin_data(days=days)

    filename = f'bitcoin_data_{days}days.csv'
    df.to_csv(filename)
    print(f"\n💾 Data save: {filename}")

    backtest_comparison(df)

    print("✅ BACKTEST FINISH")
    print(f"\n📁 Données available: {filename}")

if __name__ == "__main__":
    main()