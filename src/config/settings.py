"""Legacy settings module — kept for backwards compatibility.
Use ConfigManager.get() instead for all new code.
"""

from src.config.manager import ConfigManager


def get_settings() -> ConfigManager:
    """Returns ConfigManager singleton (backwards compatible)."""
    return ConfigManager.get()
