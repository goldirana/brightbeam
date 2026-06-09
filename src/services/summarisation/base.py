from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers.
    Swap between OpenRouter, direct OpenAI, Anthropic, etc.
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a completion from the LLM."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        ...
