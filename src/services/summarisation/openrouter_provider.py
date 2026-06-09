import httpx

from .base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """LLM provider via OpenRouter API (supports Claude, GPT, Gemini, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-sonnet-4",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._base_url = "https://openrouter.ai/api/v1"

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": self._max_tokens,
                    "temperature": self._temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    @property
    def model_name(self) -> str:
        return self._model
