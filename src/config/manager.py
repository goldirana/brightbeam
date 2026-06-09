"""
ConfigManager — Simple singleton via module-level instance.
Access anywhere via: ConfigManager.get()

All variables, paths, prompts, categories, stop words, NER patterns
are accessed through this single class. Change config.yaml -> changes propagate everywhere.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# ─── Hard-coded project root ─────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENV_PATH = PROJECT_ROOT / ".env"


class ConfigManager:
    """Configuration manager. One source of truth for the entire application."""

    _instance = None

    def __init__(self):
        # Load .env for secrets
        load_dotenv(ENV_PATH)

        # Load config.yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                self._config: dict[str, Any] = yaml.safe_load(f) or {}
        else:
            self._config = {}

    @classmethod
    def get(cls) -> "ConfigManager":
        """Get the singleton instance. Created once, reused everywhere."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ─── Paths ────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("data_dir", "data")

    @property
    def examples_dir(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("examples_dir", "data/examples")

    @property
    def test_dir(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("test_dir", "data/to-summarise")

    @property
    def output_dir(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("output_dir", "output")

    @property
    def centroids_path(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("centroids_file", "output/centroids.json")

    @property
    def prompts_dir(self) -> Path:
        return PROJECT_ROOT / self._config.get("paths", {}).get("prompts_dir", "prompts")

    # ─── Models ───────────────────────────────────────────────

    @property
    def summarisation_model(self) -> dict[str, Any]:
        return self._config.get("models", {}).get("summarisation", {})

    @property
    def judge_model(self) -> dict[str, Any]:
        return self._config.get("models", {}).get("judge", {})

    @property
    def embedding_config(self) -> dict[str, Any]:
        return self._config.get("embedding", {})

    # ─── Secrets (from .env) ──────────────────────────────────

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    # ─── Pipeline Settings ────────────────────────────────────

    @property
    def max_retries(self) -> int:
        return self._config.get("pipeline", {}).get("max_retries", 2)

    @property
    def pass_threshold(self) -> float:
        return self._config.get("pipeline", {}).get("pass_threshold", 0.8)

    @property
    def max_summary_chars(self) -> int:
        return self._config.get("pipeline", {}).get("max_summary_chars", 1500)

    @property
    def company_name(self) -> str:
        return self._config.get("pipeline", {}).get("company_name", "COMPANY")

    # ─── Categories ───────────────────────────────────────────

    @property
    def categories(self) -> dict[str, dict]:
        return self._config.get("categories", {})

    def get_category_keywords(self, category: str) -> list[str]:
        return self.categories.get(category, {}).get("keywords", [])

    # ─── Stop Words ───────────────────────────────────────────

    @property
    def stop_words(self) -> set[str]:
        return set(self._config.get("stop_words", []))

    # ─── NER Patterns ─────────────────────────────────────────

    @property
    def ner_patterns(self) -> dict[str, re.Pattern]:
        raw = self._config.get("ner_patterns", {})
        return {label: re.compile(pattern, re.IGNORECASE) for label, pattern in raw.items()}

    # ─── Feature Extraction Settings ──────────────────────────

    @property
    def top_keywords(self) -> int:
        return self._config.get("feature_extraction", {}).get("top_keywords", 10)

    @property
    def tfidf_max_features(self) -> int:
        return self._config.get("feature_extraction", {}).get("tfidf_max_features", 5000)

    @property
    def tfidf_ngram_range(self) -> tuple[int, int]:
        r = self._config.get("feature_extraction", {}).get("tfidf_ngram_range", [1, 2])
        return (r[0], r[1])

    # ─── Prompts (loaded from files) ──────────────────────────

    def load_prompt(self, relative_path: str, **variables) -> str:
        """Load a prompt file and substitute variables."""
        prompt_path = self.prompts_dir / relative_path
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        text = prompt_path.read_text(encoding="utf-8")

        # Inject standard variables
        variables.setdefault("max_summary_chars", str(self.max_summary_chars))
        variables.setdefault("company_name", self.company_name)

        # Substitute {variable} placeholders
        for key, value in variables.items():
            text = text.replace(f"{{{key}}}", str(value))

        return text

    def get_system_prompt(self, category: str) -> str:
        """Build full system prompt = base + category guidance + output format."""
        prompts_cfg = self._config.get("prompts", {})

        base = self.load_prompt(prompts_cfg.get("system_base", "system/base.txt"))
        output_fmt = self.load_prompt(prompts_cfg.get("output_format", "system/output_format.txt"))

        category_file = f"category/{category}.txt"
        category_path = self.prompts_dir / category_file
        if category_path.exists():
            category_guidance = self.load_prompt(category_file)
        else:
            category_guidance = self.load_prompt("category/general_enquiry.txt")

        return f"{base}\n\n{category_guidance}\n\n{output_fmt}"

    def get_judge_system_prompt(self) -> str:
        """Load judge system prompt."""
        prompts_cfg = self._config.get("prompts", {})
        return self.load_prompt(prompts_cfg.get("judge_system", "judge/system.txt"))

    def get_judge_evaluate_prompt(self, transcript: str, summary: str, entities: str) -> str:
        """Load judge evaluation prompt with variables."""
        prompts_cfg = self._config.get("prompts", {})
        return self.load_prompt(
            prompts_cfg.get("judge_evaluate", "judge/evaluate.txt"),
            transcript=transcript,
            summary=summary,
            entities=entities,
        )

    def get_retry_prompt(self, transcript: str, previous_summary: str, feedback: str) -> str:
        """Load retry prompt with variables."""
        prompts_cfg = self._config.get("prompts", {})
        return self.load_prompt(
            prompts_cfg.get("retry", "system/retry.txt"),
            transcript=transcript,
            previous_summary=previous_summary,
            feedback=feedback,
        )

    # ─── LLM Provider Factory ─────────────────────────────────

    def create_llm(self, role: str = "summarisation"):
        """Factory: create LLM provider based on config.
        role: 'summarisation' or 'judge'
        """
        from src.services.summarisation.openrouter_provider import OpenRouterProvider

        model_cfg = self.summarisation_model if role == "summarisation" else self.judge_model
        provider = model_cfg.get("provider", "openrouter")

        if provider == "openrouter":
            return OpenRouterProvider(
                api_key=self.openrouter_api_key,
                model=model_cfg.get("model", "anthropic/claude-sonnet-4"),
                temperature=model_cfg.get("temperature", 0.3),
                max_tokens=model_cfg.get("max_tokens", 2000),
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Add it to ConfigManager.create_llm()")
