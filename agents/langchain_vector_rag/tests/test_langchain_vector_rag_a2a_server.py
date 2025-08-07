"""
Test suite for LangChain Vector RAG A2A server implementation.

Tests the A2A protocol wrapper for the LangChain Vector RAG agent, including:
- Input extraction and validation
- Agent execution with proper mocking
- Response formatting with artifacts
- Error handling scenarios
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from a2a.types import Message, DataPart, Part
from a2a.server.tasks.task_updater import TaskUpdater

# Import agent-specific modules
from agents.langchain_vector_rag.langchain_vector_rag_a2a_server import LangChainVectorRAGA2AExecutor, LangChainVectorRAGAgentCardBuilder
from agents.langchain_vector_rag._internal.langchain_vector_rag_state import RAGInput, RAGOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError


class TestLangChainVectorRAGA2AExecutor:
    """Test cases for LangChainVectorRAGA2AExecutor."""
    
    @pytest.fixture
    def mock_rag_agent(self):
        """Create a mock RAG agent."""
        agent = Mock()
        agent.name = "LangChainVectorRAG"
        agent.id = "langchain_vector_rag-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_rag_agent):
        """Create an executor instance with mock agent."""
        return LangChainVectorRAGA2AExecutor(mock_rag_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid RAG input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Explain the main features of LangChain for building RAG applications",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/langchain_rag_project",
            "current_task": {
                "task_id": "rag-query-task-001",
                "task_status": "INPROGRESS",
                "description": "Query RAG system about LangChain features"
            },
            "chat_history": [["user", "Tell me about LangChain RAG features"], ["assistant", "I'll search for information about LangChain RAG"]],
            
            # RAGQueryInput specific fields (inherited by RAGInput)
            "query": "What are the main features of LangChain for building RAG applications?"
        }
    
    @pytest.fixture
    def valid_message(self, valid_input):
        """Create a valid A2A message with agent input."""
        return Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": valid_input}))
            ]
        )
    
    @pytest.mark.asyncio
    async def test_extract_input_success(self, executor, valid_message):
        """Test successful input extraction."""
        result = await executor._extract_input(valid_message)
        
        # Assert input type and field values
        assert isinstance(result, RAGInput)
        # RAGInput inherits from RAGQueryInput which has query field
        assert result.query == "What are the main features of LangChain for building RAG applications?"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_query(self, executor):
        """Test input extraction with missing query (which maps to user_query)."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW",
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"}
                    # Missing query field
                }}))
            ]
        )
        
        # The model validation will fail when required query field is missing
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        # Check that the error mentions the missing query field
        assert "query" in str(exc_info.value) and "required" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_rag_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required RAGOutput fields
        from models.constants import RagResponseType
        
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "metadata": {
                "retrieved_documents": 3,
                "processing_time": 1.2
            },
            "response_type": RagResponseType.ANSWERED,
            "response": "LangChain provides several key features for RAG applications: 1) Document loaders for various formats, 2) Vector stores for similarity search, 3) Retrieval chains for context augmentation..."
        }
        
        mock_rag_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = RAGInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, RAGOutput)
        assert result.response_type == RagResponseType.ANSWERED
        assert "LangChain provides several key features" in result.response
        assert result.metadata["retrieved_documents"] == 3
        
        # Verify the mock was called with correct state
        mock_rag_agent.graph.invoke.assert_called_once()
        call_args = mock_rag_agent.graph.invoke.call_args[0][0]
        assert call_args["query"] == valid_input["query"]
        assert "metadata" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_rag_agent, valid_input):
        """Test agent execution failure."""
        mock_rag_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = RAGInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "LangChain Vector RAG execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_sources(self, executor):
        """Test response formatting with retrieved sources."""
        # Create mock output with sources
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = RAGOutput(
            current_task=Task(task_id="task-1", description="RAG task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={
                "retrieved_documents": 4,
                "sources": [
                    {"title": "Vector Search Guide", "chunk_id": "chunk_1", "score": 0.94},
                    {"title": "Similarity Algorithms", "chunk_id": "chunk_2", "score": 0.87}
                ]
            },
            response_type=RagResponseType.ANSWERED,
            response="Vector similarity search is a technique used to find documents or data points that are semantically similar to a query vector."
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent messages were sent (text summary + data output)
        assert updater.new_agent_message.call_count == 2
        # Check the data message (second call) - it should be a positional argument (list of Parts)
        data_call_args = updater.new_agent_message.call_args_list[1][0][0]  # First positional arg, first part
        assert hasattr(data_call_args[0], 'root')
        assert hasattr(data_call_args[0].root, 'data')
        assert "agent_output" in data_call_args[0].root.data
        
        # Verify artifact was added for metadata
        updater.add_artifact.assert_called_once()
        artifact_call = updater.add_artifact.call_args[1]
        assert artifact_call["name"] == "Retrieved Context"
        assert artifact_call["artifact_id"] == "retrieved-context"
        # The metadata should be in the data part of the artifact
        artifact_data = artifact_call["parts"][0].root.data
        assert "retrieved_documents" in artifact_data
    
    @pytest.mark.asyncio
    async def test_format_response_no_sources(self, executor):
        """Test response formatting without sources."""
        # Create output without sources
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = RAGOutput(
            current_task=Task(task_id="task-1", description="RAG task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={},
            response_type=RagResponseType.NOT_ANSWERED,
            response="Unable to find relevant information about machine learning in the knowledge base."
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent messages were sent (text summary + data output)
        assert updater.new_agent_message.call_count == 2
        
        # Verify no artifacts were added (no sources)
        updater.add_artifact.assert_not_called()


class TestLangChainVectorRAGAgentCardBuilder:
    """Test cases for LangChainVectorRAGAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = LangChainVectorRAGAgentCardBuilder("LangChainVectorRAG", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "vector-retrieval"
        assert skills[0].name == "Vector-based Retrieval"
        assert "rag" in skills[0].tags
        assert "vectors" in skills[0].tags
        assert "langchain" in skills[0].tags
        
        assert skills[1].id == "augmented-generation"
        assert skills[1].name == "Augmented Response Generation"
        assert "generation" in skills[1].tags
        assert "augmented" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = LangChainVectorRAGAgentCardBuilder("LangChainVectorRAG", "1.0.0")
        card = (builder
                .with_description("Test LangChain Vector RAG agent")
                .with_url("http://localhost:8009/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod LangChainVectorRAG Agent"
        assert card.description == "Test LangChain Vector RAG agent"
        assert card.url == "http://localhost:8009/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.langchain_vector_rag.langchain_vector_rag_a2a_server import create_langchain_vector_rag_a2a_app
    
    # Mock dependencies
    with patch('agents.langchain_vector_rag.langchain_vector_rag_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.langchain_vector_rag.langchain_vector_rag_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8009,
                description="Test LangChain Vector RAG agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "LangChainVectorRAG"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_langchain_vector_rag_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod LangChain Vector RAG Agent (A2A)"
            assert app.description == "Test LangChain Vector RAG agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes