try:
    from .ai_signal_filter import AISignalFilter
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AISignalFilter = None

__all__ = ['AISignalFilter', 'AI_AVAILABLE']
