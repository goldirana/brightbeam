from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding providers.
    Swap between OpenAI, sentence-transformers, etc.
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a text."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...
