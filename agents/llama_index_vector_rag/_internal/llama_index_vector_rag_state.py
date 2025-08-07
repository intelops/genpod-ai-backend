from pydantic import Field
from core.state import RAGQueryInput, RAGQueryOutput, RAGQueryState


class LlamaIndexVectorInput(RAGQueryInput):
    """
    Input state for the RAG Agent.

    Inherits all fields from RAGQueryInput. No additional fields are defined.
    """
    pass


class LlamaIndexVectorOutput(RAGQueryOutput):
    """
    Output state for the RAG Agent.

    Inherits all fields from RAGQueryOutput with additional RAG-specific fields.
    """
    pass


class LlamaIndexVectorState(RAGQueryState):
    """
    Internal state for the RAG Agent.
    """
    pass
