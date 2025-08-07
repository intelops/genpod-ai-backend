"""
Test suite for Research A2A server implementation.

Tests the A2A protocol wrapper for the Research agent, including:
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
from agents.research.research_a2a_server import ResearchA2AExecutor, ResearchAgentCardBuilder
from agents.research._internal.research_state import ResearchInput, ResearchOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError


class TestResearchA2AExecutor:
    """Test cases for ResearchA2AExecutor."""
    
    @pytest.fixture
    def mock_research_agent(self):
        """Create a mock research agent."""
        agent = Mock()
        agent.name = "Research"
        agent.id = "research-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_research_agent):
        """Create an executor instance with mock agent."""
        return ResearchA2AExecutor(mock_research_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid research input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Research best practices for microservices architecture implementation",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/microservices_research",
            "current_task": {
                "task_id": "research-task-001",
                "task_status": "INPROGRESS",
                "description": "Research microservices architecture patterns and best practices"
            },
            "chat_history": [["user", "Research microservices best practices"], ["assistant", "I'll research comprehensive microservices patterns"]],
            
            # RAGQueryInput specific fields (inherited by ResearchInput)
            "query": "What are the best practices for implementing microservices architecture?"
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
        assert isinstance(result, ResearchInput)
        # ResearchInput inherits from RAGQueryInput which has query field
        assert result.query == "What are the best practices for implementing microservices architecture?"
    
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
                    # Missing query field
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "query" in str(exc_info.value) and "required" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_research_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required ResearchOutput fields
        from models.constants import RagResponseType
        
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "metadata": {
                "document_sources": ["source1.pdf", "source2.html"],
                "search_results_count": 15
            },
            "response_type": RagResponseType.ANSWERED,
            "response": "Microservices architecture best practices include: 1) Domain-driven design, 2) Independent deployment, 3) Fault tolerance patterns..."
        }
        
        mock_research_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = ResearchInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, ResearchOutput)
        assert result.response_type == RagResponseType.ANSWERED
        assert "Microservices architecture best practices" in result.response
        assert result.metadata["search_results_count"] == 15
        
        # Verify the mock was called with correct state
        mock_research_agent.graph.invoke.assert_called_once()
        call_args = mock_research_agent.graph.invoke.call_args[0][0]
        assert call_args["query"] == valid_input["query"]
        assert "metadata" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_research_agent, valid_input):
        """Test agent execution failure."""
        mock_research_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = ResearchInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Research execution failed" in str(exc_info.value)
        assert "Graph execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_sources(self, executor):
        """Test response formatting with metadata."""
        # Create mock output with metadata
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = ResearchOutput(
            current_task=Task(task_id="task-1", description="Research task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={
                "search_results_count": 10,
                "sources": [
                    {"title": "Microservices Patterns", "url": "https://example.com/patterns"},
                    {"title": "Building Microservices", "url": "https://example.com/building"}
                ]
            },
            response_type=RagResponseType.ANSWERED,
            response="Best practices include domain-driven design, independent deployment, and fault tolerance."
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
        assert artifact_call["name"] == "Research Metadata"
        assert artifact_call["artifact_id"] == "research-metadata"
        # The metadata should be in the data part of the artifact
        artifact_data = artifact_call["parts"][0].root.data
        assert "search_results_count" in artifact_data
    
    @pytest.mark.asyncio
    async def test_format_response_no_sources(self, executor):
        """Test response formatting without metadata."""
        # Create output without metadata
        from models.models import Task
        from models.constants import ChatRoles, RagResponseType
        
        output = ResearchOutput(
            current_task=Task(task_id="task-1", description="Research task"),
            chat_history=[(ChatRoles.USER, "test message")],
            metadata={},
            response_type=RagResponseType.NOT_ANSWERED,
            response="Unable to find specific information about microservices."
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


class TestResearchAgentCardBuilder:
    """Test cases for ResearchAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = ResearchAgentCardBuilder("Research", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "information-retrieval"
        assert skills[0].name == "Information Retrieval"
        assert "research" in skills[0].tags
        assert "retrieval" in skills[0].tags
        
        assert skills[1].id == "web-search"
        assert skills[1].name == "Web Search Integration"
        assert "search" in skills[1].tags
        assert "web" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = ResearchAgentCardBuilder("Research", "1.0.0")
        card = (builder
                .with_description("Test research agent")
                .with_url("http://localhost:8008/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod Research Agent"
        assert card.description == "Test research agent"
        assert card.url == "http://localhost:8008/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.research.research_a2a_server import create_research_a2a_app
    
    # Mock dependencies
    with patch('agents.research.research_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.research.research_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8008,
                description="Test research agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Research"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_research_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Research Agent (A2A)"
            assert app.description == "Test research agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes