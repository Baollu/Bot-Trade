"""
Nexus Trade - Strategies Package
Stratégies de trading prouvées + Filtre IA
"""

__version__ = "2.0.0"
__author__ = "Nexus Trade"

# Exports pour utilisation facile
from .classic_strategy.proven_strategies import ProvenStrategies

try:
    from .ai.ai_signal_filter import AISignalFilter
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AISignalFilter = None

__all__ = ['ProvenStrategies', 'AISignalFilter', 'AI_AVAILABLE']
