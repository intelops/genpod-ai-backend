"""
Test suite for RAG Middleware A2A server implementation.

Tests the A2A protocol wrapper for the RAG Middleware agent, including:
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
from agents.rag_middleware.rag_middleware_a2a_server import RAGMiddlewareA2AExecutor, RAGMiddlewareAgentCardBuilder
from agents.rag_middleware._internal.rag_middleware_state import RAGMiddlewareInput, RAGMiddlewareOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.constants import RagResponseType
from models.rag_middleware_models import RagAgentDetail


class TestRAGMiddlewareA2AExecutor:
    """Test cases for RAGMiddlewareA2AExecutor."""
    
    @pytest.fixture
    def mock_rag_middleware(self):
        """Create a mock RAG middleware agent."""
        agent = Mock()
        agent.name = "RAGMiddleware"
        agent.id = "rag_middleware-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_rag_middleware):
        """Create an executor instance with mock agent."""
        return RAGMiddlewareA2AExecutor(mock_rag_middleware)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid RAG middleware input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Help me implement authentication in a Flask REST API",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/flask_auth_project",
            "current_task": {
                "task_id": "auth-implementation-task-001",
                "task_status": "INPROGRESS",
                "description": "Implement authentication system for Flask REST API"
            },
            "chat_history": [["user", "I need help with Flask authentication"], ["assistant", "I'll help you with Flask authentication implementation"]],
            
            # RAGMiddlewareInput specific fields
            "agent_id": "coder-agent-001",
            "task_id": "task-456",
            "query": "How do I implement authentication in a REST API using Python Flask?"
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
        assert isinstance(result, RAGMiddlewareInput)
        assert result.agent_id == "coder-agent-001"
        assert result.task_id == "task-456"
        assert result.query == "How do I implement authentication in a REST API using Python Flask?"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_agent_id(self, executor):
        """Test input extraction with missing agent_id."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW",
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"},
                    "task_id": "task-456",
                    "query": "Test query"
                    # Missing agent_id
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "agent_id" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_task_id(self, executor):
        """Test input extraction with missing task_id."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW",
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"},
                    "agent_id": "test-agent",
                    "query": "Test query"
                    # Missing task_id
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "task_id" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_query(self, executor):
        """Test input extraction with missing query."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW",
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"},
                    "agent_id": "test-agent",
                    "task_id": "task-456"
                    # Missing query
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "query" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_rag_middleware, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required RAGMiddlewareOutput fields
        from models.constants import RagResponseType
        
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "response_type": RagResponseType.ANSWERED,
            "response": "To implement authentication in Flask, you can use Flask-Login extension. Here's a basic setup: 1) Install Flask-Login, 2) Configure user session management, 3) Create login/logout routes...",
            "selected_rag_agent": {
                "name": "langchain_vector_rag",
                "confidence": 0.92,
                "specialization": "Python development"
            },
            "selection_details": {
                "langchain_vector_rag": {
                    "confidence": 0.92,
                    "reason": "High confidence for Python Flask authentication query"
                },
                "llama_index_vector_rag": {
                    "confidence": 0.78,
                    "reason": "Good match but lower confidence than LangChain agent"
                }
            }
        }
        
        mock_rag_middleware.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = RAGMiddlewareInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, RAGMiddlewareOutput)
        assert result.response_type == "rag_answered"
        assert "Flask-Login extension" in result.response
        assert result.selected_rag_agent["name"] == "langchain_vector_rag"
        assert result.selected_rag_agent["confidence"] == 0.92
        assert len(result.selection_details) == 2
        assert "langchain_vector_rag" in result.selection_details
        assert "llama_index_vector_rag" in result.selection_details
        
        # Verify the mock was called with correct state
        mock_rag_middleware.graph.invoke.assert_called_once()
        call_args = mock_rag_middleware.graph.invoke.call_args[0][0]
        assert call_args["agent_id"] == valid_input["agent_id"]
        assert call_args["task_id"] == valid_input["task_id"]
        assert call_args["query"] == valid_input["query"]
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_rag_middleware, valid_input):
        """Test agent execution failure."""
        mock_rag_middleware.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = RAGMiddlewareInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "RAG Middleware execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_selection_details(self, executor):
        """Test response formatting with agent selection details."""
        # Create mock output with selection details
        from models.models import Task
        from models.constants import ChatRoles
        
        output = RAGMiddlewareOutput(
            current_task=Task(task_id="task-1", description="RAG middleware task"),
            chat_history=[(ChatRoles.USER, "test message")],
            response_type=RagResponseType.ANSWERED,
            response="Flask authentication can be implemented using Flask-Login and Flask-Session extensions.",
            selected_rag_agent={
                "name": "langchain_vector_rag",
                "confidence": 0.89,
                "specialization": "Web development"
            },
            selection_details={
                "langchain_vector_rag": RagAgentDetail(
                    confidence=0.89,
                    reason="High confidence for web development query"
                ),
                "llama_index_vector_rag": RagAgentDetail(
                    confidence=0.73,
                    reason="Moderate confidence, less specialized"
                )
            }
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
        
        # Verify artifact was added for selection details
        updater.add_artifact.assert_called_once()
        artifact_call = updater.add_artifact.call_args[1]
        assert artifact_call["name"] == "RAG Agent Selection Details"
        assert artifact_call["artifact_id"] == "selection-details"
        # The selection_details should be in the data part of the artifact
        artifact_data = artifact_call["parts"][0].root.data
        assert "selection_details" in artifact_data
    
    @pytest.mark.asyncio
    async def test_format_response_no_selection_details(self, executor):
        """Test response formatting without selection details."""
        # Create output without selection details
        from models.models import Task
        from models.constants import ChatRoles
        
        output = RAGMiddlewareOutput(
            current_task=Task(task_id="task-1", description="RAG middleware task"),
            chat_history=[(ChatRoles.USER, "test message")],
            response_type=RagResponseType.NO_AGENT_AVAILABLE,
            response="Unable to find a suitable RAG agent for this query.",
            selected_rag_agent={},
            selection_details={}
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
        
        # Verify no artifacts were added (no selection details)
        updater.add_artifact.assert_not_called()


class TestRAGMiddlewareAgentCardBuilder:
    """Test cases for RAGMiddlewareAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = RAGMiddlewareAgentCardBuilder("RAGMiddleware", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 3
        assert skills[0].id == "rag-agent-selection"
        assert skills[0].name == "RAG Agent Selection"
        assert "rag" in skills[0].tags
        assert "middleware" in skills[0].tags
        assert "selection" in skills[0].tags
        
        assert skills[1].id == "query-caching"
        assert skills[1].name == "Query Response Caching"
        assert "cache" in skills[1].tags
        assert "optimization" in skills[1].tags
        
        assert skills[2].id == "error-tracking"
        assert skills[2].name == "Error and Task Tracking"
        assert "monitoring" in skills[2].tags
        assert "error-handling" in skills[2].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = RAGMiddlewareAgentCardBuilder("RAGMiddleware", "1.0.0")
        card = (builder
                .with_description("Test RAG middleware agent")
                .with_url("http://localhost:8011/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod RAGMiddleware Agent"
        assert card.description == "Test RAG middleware agent"
        assert card.url == "http://localhost:8011/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 3


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.rag_middleware.rag_middleware_a2a_server import create_rag_middleware_a2a_app
    
    # Mock dependencies
    with patch('agents.rag_middleware.rag_middleware_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.rag_middleware.rag_middleware_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8011,
                description="Test RAG middleware agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "RAGMiddleware"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_rag_middleware_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod RAG Middleware Agent (A2A)"
            assert app.description == "Test RAG middleware agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes