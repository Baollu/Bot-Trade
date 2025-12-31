#!/usr/bin/env python3

import pandas as pd
import time
import requests
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

import sys

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from ai.ai_signal_filter import AISignalFilter
from classic_strategy.proven_strategies import ProvenStrategies


class DailyCircuitBreaker:
    def __init__(self, max_daily_loss_percent=10):
        self.max_daily_loss_percent = max_daily_loss_percent
        self.daily_start_balance = None
        self.current_balance = None
        self.is_paused = False
        self.pause_until = None
        self.consecutive_losses = 0

    def start_day(self, balance):
        self.daily_start_balance = balance
        self.current_balance = balance
        self.is_paused = False
        self.pause_until = None
        print(f"\n🌅 New day wallet: ${balance:,.2f}")

    def check_can_trade(self):
        if self.pause_until and datetime.now() >= self.pause_until:
            self.is_paused = False
            self.pause_until = None
            self.consecutive_losses = 0

        if self.is_paused:
            remaining = (self.pause_until - datetime.now()).seconds // 3600
            return False, f"⏸️ Pause until tomorrow (~{remaining}h remains)"

        if self.daily_start_balance:
            daily_loss = (self.daily_start_balance - self.current_balance) / self.daily_start_balance * 100

            if daily_loss >= self.max_daily_loss_percent:
                tomorrow = datetime.now() + timedelta(days=1)
                self.pause_until = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                self.is_paused = True

                return False, f"🛑 Lose daily -{daily_loss:.1f}%. Break until tomorrow"

        return True, "✅ OK for trade"

    def update_balance(self, new_balance, was_win):
        self.current_balance = new_balance

        if was_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

    def get_status(self):
        if not self.daily_start_balance:
            return {"status": "not_started"}

        daily_pnl = self.current_balance - self.daily_start_balance
        daily_pnl_percent = (daily_pnl / self.daily_start_balance) * 100

        return {
            "status": "paused" if self.is_paused else "active",
            "daily_start": self.daily_start_balance,
            "current": self.current_balance,
            "daily_pnl": daily_pnl,
            "daily_pnl_percent": daily_pnl_percent,
            "consecutive_losses": self.consecutive_losses,
            "pause_until": self.pause_until.strftime("%Y-%m-%d %H:%M") if self.pause_until else None
        }


class TradingBot:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.circuit_breaker = DailyCircuitBreaker(
            max_daily_loss_percent=self.config['max_daily_loss_percent']
        )

        if self.config['use_ai_filter']:
            try:
                ai_model_path = self.config.get('ai_model_path', '../ai/signal_filter.pkl')
                if not os.path.isabs(ai_model_path):
                    ai_model_path = str(parent_dir / ai_model_path.lstrip('../'))

                self.strategy = AISignalFilter(model_path=ai_model_path)
                print("✅ Stratégie IA load")
            except FileNotFoundError:
                print("⚠️ Model IA not found")
                self.strategy = ProvenStrategies()
        else:
            self.strategy = ProvenStrategies()

        self.balance = self.config['initial_balance']
        self.positions = {}
        self.trades_history = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def load_config(self, config_file):
        default_config = {
            "initial_balance": 10000,
            "max_daily_loss_percent": 10,
            "position_size_percent": 2,
            "stop_loss_percent": 2,
            "take_profit_percent": 3,
            "min_confidence": 0.65,
            "max_positions": 5,
            "check_interval_minutes": 5,
            "use_ai_filter": True,
            "ai_model_path": "../ai/signal_filter.pkl",
            "symbol": "BTCUSDT",
            "dry_run": True
        }

        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def get_market_data(self, symbol='BTCUSDT', interval='1h', limit=200):
        url = "https://api.binance.com/api/v3/klines"

        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        try:
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

        except Exception as e:
            print(f"❌ Erreur récupération données: {e}")
            return None

    def analyze_market(self, df):
        return self.strategy.analyze(df)

    def calculate_position_size(self, price):
        position_value = self.balance * (self.config['position_size_percent'] / 100)
        amount = position_value / price
        return amount, position_value

    def open_position(self, symbol, signal, current_price):
        amount, value = self.calculate_position_size(current_price)
        stop_loss = current_price * (1 - self.config['stop_loss_percent'] / 100)
        take_profit = current_price * (1 + self.config['take_profit_percent'] / 100)
        self.positions[symbol] = {
            'amount': amount,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': datetime.now(),
            'signal': signal
        }

        self.balance -= value

        trade = {
            'type': 'BUY',
            'symbol': symbol,
            'amount': amount,
            'price': current_price,
            'value': value,
            'time': datetime.now(),
            'confidence': signal['confidence'],
            'reasons': signal['reasons']
        }
        self.trades_history.append(trade)
        self.total_trades += 1

        print("Position open")
        print(f"💰 {symbol}: {amount:.6f} à ${current_price:,.2f}")
        print(f"📊 Valeur: ${value:,.2f} ({self.config['position_size_percent']}% du capital)")
        print(f"🛡️ Stop-loss: ${stop_loss:,.2f} (-{self.config['stop_loss_percent']}%)")
        print(f"🎯 Take-profit: ${take_profit:,.2f} (+{self.config['take_profit_percent']}%)")
        print(f"🎲 Confiance: {signal['confidence']:.0%}")

        if self.config['dry_run']:
            print(f"⚠️  MODE SIMULATION - Aucun ordre réel passé")

        return True

    def close_position(self, symbol, current_price, reason):

        if symbol not in self.positions:
            return False

        pos = self.positions[symbol]

        entry_value = pos['amount'] * pos['entry_price']
        exit_value = pos['amount'] * current_price
        pnl = exit_value - entry_value
        pnl_percent = (pnl / entry_value) * 100

        self.balance += exit_value

        if pnl > 0:
            self.winning_trades += 1
            was_win = True
        else:
            self.losing_trades += 1
            was_win = False

        trade = {
            'type': 'SELL',
            'symbol': symbol,
            'amount': pos['amount'],
            'entry_price': pos['entry_price'],
            'exit_price': current_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'time': datetime.now(),
            'reason': reason,
            'duration': (datetime.now() - pos['entry_time']).seconds // 60
        }
        self.trades_history.append(trade)

        # Met à jour circuit breaker
        self.circuit_breaker.update_balance(self.balance, was_win)

        print(f"Position close")
        print(f"💰 {symbol}: {pos['amount']:.6f}")
        print(f"📈 Entrée: ${pos['entry_price']:,.2f}")
        print(f"📉 Sortie: ${current_price:,.2f}")
        print(f"💵 P&L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)")
        print(f"📝 Raison: {reason}")
        print(f"⏱️ Durée: {trade['duration']} min")
        print(f"💰 Balance: ${self.balance:,.2f}")

        del self.positions[symbol]

        if self.config['dry_run']:
            print(f"⚠️  MODE SIMULATION")

        return True

    def check_positions(self, current_price):

        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]

            if current_price <= pos['stop_loss']:
                self.close_position(symbol, current_price, f"Stop-loss atteint (${pos['stop_loss']:,.2f})")

            elif current_price >= pos['take_profit']:
                self.close_position(symbol, current_price, f"Take-profit atteint (${pos['take_profit']:,.2f})")

    def run_trading_cycle(self):
        print(f"\n{'━' * 70}")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'━' * 70}")

        # Récupère données marché
        df = self.get_market_data(self.config['symbol'])
        if df is None:
            print("Impossible to fetch data")
            return

        current_price = df['close'].iloc[-1]
        print(f"💰 {self.config['symbol']}: ${current_price:,.2f}")
        print(f"💵 Balance: ${self.balance:,.2f}")
        print(f"📊 Positions: {len(self.positions)}")

        self.check_positions(current_price)

        can_trade, message = self.circuit_breaker.check_can_trade()

        if not can_trade:
            print(f"\n{message}")

            status = self.circuit_breaker.get_status()
            if status['status'] == 'paused':
                print(f"📊 Lose today: ${status['daily_pnl']:,.2f} ({status['daily_pnl_percent']:.2f}%)")
                print(f"🔄 Resume: {status['pause_until']}")

            return

        if len(self.positions) >= self.config['max_positions']:
            print(f"⏸️ Number of position hit ({self.config['max_positions']})")
            return

        signal = self.analyze_market(df)

        print(f"\n📊 Signal: {signal['decision']} (Confiance: {signal['confidence']:.0%})")

        if signal.get('ai_filter'):
            print(f"🤖 Filtre IA: {signal['ai_filter']}")

        if signal['decision'] == 'BUY' and signal['confidence'] >= self.config['min_confidence']:
            if self.config['symbol'] not in self.positions:
                self.open_position(self.config['symbol'], signal, current_price)

        elif signal['decision'] == 'SELL' and self.config['symbol'] in self.positions:
            self.close_position(self.config['symbol'], current_price, "Signal de vente")

        else:
            print(f"⏸️ No action")

    def print_daily_summary(self):
        status = self.circuit_breaker.get_status()

        if status['status'] == 'not_started':
            return

        print(f"📊 Daily recap")
        print(f"💰 Capital début: ${status['daily_start']:,.2f}")
        print(f"💵 Capital actuel: ${status['current']:,.2f}")
        print(f"📈 P&L journalier: ${status['daily_pnl']:+,.2f} ({status['daily_pnl_percent']:+.2f}%)")
        print(f"📊 Trades aujourd'hui: {self.total_trades}")
        print(f"✅ Gagnants: {self.winning_trades}")
        print(f"Perdants: {self.losing_trades}")

        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
            print(f"🎯 Win rate: {win_rate:.1f}%")

        if status['status'] == 'paused':
            print(f"\n🛑 Status: PAUSE until {status['pause_until']}")
        else:
            print(f"\n✅ Status: ACTIF")

    def run(self):

        print(f"🚀 Bot start")

        if self.config['dry_run']:
            print(f"⚠️  MODE SIMULATION ACTIVATE")
        else:
            print(f"🔴 MODE REEL ACTIVATE")
            print(f"   Order pass on Binance")

        self.circuit_breaker.start_day(self.balance)

        iteration = 0

        try:
            while True:
                iteration += 1

                self.run_trading_cycle()

                if iteration % 12 == 0:
                    self.print_daily_summary()

                wait_seconds = self.config['check_interval_minutes'] * 60
                print(f"\n Next verification in  {self.config['check_interval_minutes']} min...")
                time.sleep(wait_seconds)

        except KeyboardInterrupt:
            print(f"⏹️  BOT STOP")
            self.print_daily_summary()
            print(f"\n✅ Stop the system")


def main():
   if not os.path.exists('config.json'):
        default_config = {
            "initial_balance": 10000,
            "max_daily_loss_percent": 10,
            "position_size_percent": 2,
            "stop_loss_percent": 2,
            "take_profit_percent": 3,
            "min_confidence": 0.65,
            "max_positions": 5,
            "check_interval_minutes": 5,
            "use_ai_filter": True,
            "ai_model_path": "../ai/signal_filter.pkl",
            "symbol": "BTCUSDT",
            "dry_run": True
        }

        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

        print("✅ Config file create")

        bot = TradingBot()
        bot.run()


if __name__ == "__main__":
    main()