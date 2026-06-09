"""Category definitions loaded from config.yaml via ConfigManager."""

from src.config.manager import ConfigManager


def get_categories() -> dict[str, dict]:
    """Get all categories from config."""
    return ConfigManager.get().categories


def compute_domain_signals(text: str) -> dict[str, float]:
    """Score how strongly a transcript matches each category based on keyword hits."""
    cfg = ConfigManager.get()
    text_lower = text.lower()
    scores = {}

    for category, config in cfg.categories.items():
        keywords = config.get("keywords", [])
        hits = sum(1 for kw in keywords if kw in text_lower)
        total = len(keywords)
        scores[category] = hits / total if total > 0 else 0.0

    return scores
