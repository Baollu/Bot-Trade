"""
Strategy Manager - Point d'entrée principal
Choisit automatiquement entre stratégie classique ou IA
"""

import pandas as pd
from typing import Dict

# Import des stratégies
from .classic_strategy.classic_strategy import ClassicStrategy
from .with_ia.ai_strategy import AIStrategy


class StrategyManager:
    """
    Gestionnaire de stratégies
    Utilisation simple avec paramètre use_ia=True/False
    """

    def __init__(self, use_ia: bool = False, model_path: str = 'ai/crypto_predictor.onnx'):
        """
        Initialise le gestionnaire de stratégies

        Args:
            use_ia: True pour IA, False pour classique
            model_path: Chemin vers modèle ONNX (si use_ia=True)
        """
        self.use_ia = use_ia
        self.model_path = model_path

        print("\n" + "=" * 60)
        print("🚀 NEXUS TRADE v2.0 - Strategy Manager")
        print("=" * 60)

        if use_ia:
            print(f"📌 Mode sélectionné: HYBRIDE (Classique + IA)")
            self.strategy = AIStrategy(model_path=model_path)
        else:
            print(f"📌 Mode sélectionné: CLASSIQUE (Sans IA)")
            self.strategy = ClassicStrategy()

        print("=" * 60 + "\n")

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyse le marché avec la stratégie sélectionnée

        Args:
            df: DataFrame avec colonnes ['close', 'high', 'low', 'volume']

        Returns:
            Dict avec decision, confidence, signals, metrics
        """
        return self.strategy.analyze(df)

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        """
        Backtest de la stratégie

        Args:
            df: DataFrame historique
            initial_balance: Capital initial

        Returns:
            Dict avec résultats du backtest
        """
        return self.strategy.backtest(df, initial_balance)

    def get_strategy_info(self) -> Dict:
        """
        Retourne infos sur la stratégie active
        """
        return {
            'name': self.strategy.name,
            'type': 'AI_ENHANCED' if self.use_ia else 'CLASSIC',
            'ai_enabled': getattr(self.strategy, 'ai_enabled', False),
            'model_path': self.model_path if self.use_ia else None
        }


# Fonction helper pour utilisation rapide
def create_strategy(use_ia: bool = False, model_path: str = 'ai/crypto_predictor.onnx'):
    """
    Crée une stratégie rapidement

    Usage:
        # Sans IA
        strategy = create_strategy(use_ia=False)

        # Avec IA
        strategy = create_strategy(use_ia=True)
    """
    return StrategyManager(use_ia=use_ia, model_path=model_path)


if __name__ == "__main__":
    """
    Test rapide des deux stratégies
    """
    import numpy as np

    # Données fictives
    df = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 50000,
        'high': np.random.randn(100).cumsum() + 50100,
        'low': np.random.randn(100).cumsum() + 49900,
        'volume': np.random.rand(100) * 1000000
    })

    # Test stratégie classique
    print("\n" + "=" * 60)
    print("TEST 1: STRATÉGIE CLASSIQUE")
    print("=" * 60)
    strategy_classic = create_strategy(use_ia=False)
    result_classic = strategy_classic.analyze(df)
    print(f"Décision: {result_classic['decision']}")
    print(f"Confiance: {result_classic['confidence']:.0%}")

    # Test stratégie avec IA
    print("\n" + "=" * 60)
    print("TEST 2: STRATÉGIE AVEC IA")
    print("=" * 60)
    strategy_ai = create_strategy(use_ia=True)
    result_ai = strategy_ai.analyze(df)
    print(f"Décision: {result_ai['decision']}")
    print(f"Confiance: {result_ai['confidence']:.0%}")

    print("\n" + "=" * 60)
    print("✅ Tests terminés !")
    print("=" * 60)