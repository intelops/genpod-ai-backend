"""
Test suite for LlamaIndex Vector RAG A2A server implementation.

Tests the A2A protocol wrapper for the LlamaIndex Vector RAG agent, including:
- Input extraction and validation
- Agent execution with proper mocking
- Response formatting with artifacts
- Error handling scenarios
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import uuid

from a2a.types import Message, DataPart, TextPart, Part
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

# Import agent-specific modules
from agents.llama_index_vector_rag.llama_index_vector_rag_a2a_server import LlamaIndexVectorRAGA2AExecutor, LlamaIndexVectorRAGAgentCardBuilder
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_state import LlamaIndexVectorInput, LlamaIndexVectorOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError


class TestLlamaIndexVectorRAGA2AExecutor:
    """Test cases for LlamaIndexVectorRAGA2AExecutor."""
    
    @pytest.fixture
    def mock_rag_agent(self):
        """Create a mock LlamaIndex RAG agent."""
        agent = Mock()
        agent.name = "LlamaIndexVectorRAG"
        agent.id = "llama_index_vector_rag-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_rag_agent):
        """Create an executor instance with mock agent."""
        return LlamaIndexVectorRAGA2AExecutor(mock_rag_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid LlamaIndex RAG input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Explain how LlamaIndex handles document indexing and retrieval processes",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/llama_index_rag_project",
            "current_task": {
                "task_id": "llama-rag-query-task-001",
                "task_status": "INPROGRESS",
                "description": "Query LlamaIndex RAG system about document handling"
            },
            "chat_history": [["user", "How does LlamaIndex work?"], ["assistant", "I'll search for LlamaIndex documentation"]],
            
            # RAGQueryInput specific fields (inherited by LlamaIndexVectorInput)
            "query": "How does LlamaIndex handle document indexing and retrieval?"
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
        assert isinstance(result, LlamaIndexVectorInput)
        # LlamaIndexVectorInput inherits from RAGQueryInput which has query field
        assert result.query == "How does LlamaIndex handle document indexing and retrieval?"
    
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
        # Setup mock response with all required LlamaIndexVectorOutput fields
        from models.constants import RagResponseType
        
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "metadata": {
                "retrieved_nodes": 3,
                "confidence_score": 0.91,
                "index_used": "documents_index",
                "processing_time": 0.8,
                "sources": [
                    {"node_id": "node_1", "document": "LlamaIndex Guide", "score": 0.92},
                    {"node_id": "node_2", "document": "Indexing Best Practices", "score": 0.87},
                    {"node_id": "node_3", "document": "Vector Store Configuration", "score": 0.83}
                ]
            },
            "response_type": RagResponseType.ANSWERED,
            "response": "LlamaIndex handles document indexing through several key components: 1) Document loaders that parse various formats, 2) Node parsers that chunk documents, 3) Vector stores for embeddings..."
        }
        
        mock_rag_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = LlamaIndexVectorInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, LlamaIndexVectorOutput)
        assert result.response_type == RagResponseType.ANSWERED
        assert "LlamaIndex handles document indexing" in result.response
        assert result.metadata["confidence_score"] == 0.91
        assert len(result.metadata["sources"]) == 3
        
        # Verify the mock was called with correct state
        mock_rag_agent.graph.invoke.assert_called_once()
        call_args = mock_rag_agent.graph.invoke.call_args[0][0]
        assert call_args["query"] == valid_input["query"]
        assert "metadata" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_rag_agent, valid_input):
        """Test agent execution failure."""
        mock_rag_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = LlamaIndexVectorInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "LlamaIndex Vector RAG execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_sources(self, executor):
        """Test response formatting with retrieved sources."""
        # Create mock output with sources
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = LlamaIndexVectorOutput(
            current_task=Task(task_id="task-1", description="RAG task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={
                "confidence_score": 0.88,
                "retrieved_nodes": 4,
                "sources": [
                    {"node_id": "node_1", "document": "LlamaIndex Benefits", "score": 0.91},
                    {"node_id": "node_2", "document": "RAG Advantages", "score": 0.86},
                    {"node_id": "node_3", "document": "Vector Store Benefits", "score": 0.82}
                ]
            },
            response_type=RagResponseType.ANSWERED,
            response="LlamaIndex provides several benefits including easy document ingestion, flexible querying, and efficient vector storage."
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
        assert "sources" in artifact_data  # sources are in metadata now
    
    @pytest.mark.asyncio
    async def test_format_response_no_sources(self, executor):
        """Test response formatting without sources."""
        # Create output without sources
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = LlamaIndexVectorOutput(
            current_task=Task(task_id="task-1", description="RAG task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={},
            response_type=RagResponseType.NOT_ANSWERED,
            response="Unable to find relevant information about artificial intelligence in the knowledge base."
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
        
        # Verify no artifacts were added (empty metadata)
        updater.add_artifact.assert_not_called()


class TestLlamaIndexVectorRAGAgentCardBuilder:
    """Test cases for LlamaIndexVectorRAGAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = LlamaIndexVectorRAGAgentCardBuilder("LlamaIndexVectorRAG", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "vector-retrieval"
        assert skills[0].name == "Vector-based Retrieval"
        assert "rag" in skills[0].tags
        assert "vectors" in skills[0].tags
        assert "llamaindex" in skills[0].tags
        
        assert skills[1].id == "augmented-generation"
        assert skills[1].name == "Augmented Response Generation"
        assert "generation" in skills[1].tags
        assert "augmented" in skills[1].tags
        assert "llamaindex" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = LlamaIndexVectorRAGAgentCardBuilder("LlamaIndexVectorRAG", "1.0.0")
        card = (builder
                .with_description("Test LlamaIndex Vector RAG agent")
                .with_url("http://localhost:8010/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod LlamaIndexVectorRAG Agent"
        assert card.description == "Test LlamaIndex Vector RAG agent"
        assert card.url == "http://localhost:8010/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.llama_index_vector_rag.llama_index_vector_rag_a2a_server import create_llama_index_vector_rag_a2a_app
    
    # Mock dependencies
    with patch('agents.llama_index_vector_rag.llama_index_vector_rag_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.llama_index_vector_rag.llama_index_vector_rag_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8010,
                description="Test LlamaIndex Vector RAG agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "LlamaIndexVectorRAG"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_llama_index_vector_rag_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod LlamaIndex Vector RAG Agent (A2A)"
            assert app.description == "Test LlamaIndex Vector RAG agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes