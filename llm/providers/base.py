from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(self, system: str, user: str, max_tokens: int = 512) -> str:
        """Send a completion request and return the response text."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is currently available."""
        ...
