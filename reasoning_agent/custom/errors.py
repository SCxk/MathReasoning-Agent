class AgentError(Exception):
    """Base class for internal agent errors."""


class ModelBudgetExceeded(AgentError):
    """Raised when a single problem exceeds the model call budget."""


class EmptyModelResponse(AgentError):
    """Raised when the model returns no usable text."""


class InvalidModelResponse(AgentError):
    """Raised when a model response cannot be parsed into a known event."""


class InvalidToolRequest(AgentError):
    """Raised when a requested tool is not allowed or has invalid arguments."""


class ToolBudgetExceeded(AgentError):
    """Raised when a single problem exceeds the tool call budget."""
