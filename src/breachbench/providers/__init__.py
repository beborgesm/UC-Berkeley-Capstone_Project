"""Provider layer: vendor-agnostic chat + tool-calling behind one interface.

Vendor adapter modules (openai/gemini/groq) are imported lazily by the registry,
so importing this package pulls in no vendor SDK and resolves no key.
"""

from .base import AbstractProvider, ChatProvider
from .registry import build_provider
from .retry import ErrorType, ProviderError
from .stub import StubCallContext, StubProvider, text_responder
from .types import (
    ChatResponse,
    Message,
    Role,
    ToolCall,
    ToolChoice,
    ToolSpec,
    Usage,
    assistant,
    flatten_history,
    system,
    user,
)

__all__ = [
    "AbstractProvider",
    "ChatProvider",
    "ChatResponse",
    "ErrorType",
    "Message",
    "ProviderError",
    "Role",
    "StubCallContext",
    "StubProvider",
    "ToolCall",
    "ToolChoice",
    "ToolSpec",
    "Usage",
    "assistant",
    "build_provider",
    "flatten_history",
    "system",
    "text_responder",
    "user",
]
