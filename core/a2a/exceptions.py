"""
Custom exceptions for A2A protocol implementation.

Following Single Responsibility Principle - each exception handles one specific error type.
"""


class A2AError(Exception):
    """Base exception for all A2A related errors."""
    pass


class A2AConfigError(A2AError):
    """Raised when there's an error in A2A configuration."""
    pass


class A2AExecutionError(A2AError):
    """Raised when there's an error during agent execution."""
    pass


class A2AInputExtractionError(A2AError):
    """Raised when input extraction from A2A message fails."""
    pass


class A2AOutputFormattingError(A2AError):
    """Raised when output formatting to A2A response fails."""
    pass


class A2ATaskManagementError(A2AError):
    """Raised when task lifecycle management fails."""
    pass