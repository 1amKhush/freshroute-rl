"""Load only known local checkpoint formats; optional RL dependencies load lazily."""

from pathlib import Path

from .agent import QAgent


def load_agent(path):
    if Path(path).is_dir():
        from .dqn import DQNAgent
        return DQNAgent.load(path)
    return QAgent.load(path)
