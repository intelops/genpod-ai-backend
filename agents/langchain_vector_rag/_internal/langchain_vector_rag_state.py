
from langchain_core.documents import Document
from pydantic import Field

from core.state import RAGQueryInput, RAGQueryOutput, RAGQueryState


class RAGInput(RAGQueryInput):
    """
    Input state for the RAG Agent.

    Inherits all fields from RAGQueryInput. No additional fields are defined.
    """
    pass


class RAGOutput(RAGQueryOutput):
    """
    Output state for the RAG Agent.

    Inherits all fields from RAGQueryOutput with additional RAG-specific fields.
    """
    pass


class RAGState(RAGQueryState):
    """
    Internal state for the RAG Agent.

    This state holds the workflow information including retrieved documents,
    counters for hallucinations and retries, and any other data needed during
    the query processing workflow.
    """

    documents: list[Document] = Field(
        default_factory=list,
        description="The list of documents retrieved from the vector store."
    )
    hallucination_count: int = Field(
        default=0,
        description="The number of hallucinations detected during the generation process."
    )
    retry_count: int = Field(
        default=0,
        description="The number of retry attempts made to generate a valid response."
    )
