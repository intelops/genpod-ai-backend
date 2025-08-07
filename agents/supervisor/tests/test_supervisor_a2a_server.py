"""
Test suite for Supervisor A2A server implementation.

Tests the A2A protocol wrapper for the Supervisor agent, including:
- Input extraction and validation
- Agent execution with proper mocking
- Response formatting with artifacts
- Error handling scenarios
"""

import sys
from unittest.mock import Mock, MagicMock

# Mock the problematic strawberry import before importing supervisor
sys.modules['strawberry.experimental.pydantic._compat'] = MagicMock()
sys.modules['strawberry.experimental.pydantic'] = MagicMock()
sys.modules['strawberry.experimental'] = MagicMock()
sys.modules['strawberry'] = MagicMock()
sys.modules['phoenix.utilities.json'] = MagicMock()
sys.modules['phoenix.experiments.functions'] = MagicMock()
sys.modules['phoenix.experiments'] = MagicMock()
sys.modules['phoenix.session.client'] = MagicMock()
sys.modules['phoenix'] = MagicMock()
sys.modules['utils.otel.otel_tracing'] = MagicMock()
sys.modules['utils.otel'] = MagicMock()

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import uuid

from a2a.types import Message, DataPart, TextPart, Part
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

# Import agent-specific modules
from agents.supervisor.supervisor_a2a_server import SupervisorA2AExecutor, SupervisorAgentCardBuilder
from agents.supervisor._internal.supervisor_state import SupervisorInput, SupervisorOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.constants import PStatus
from models.models import TaskQueue, Task, IssuesQueue, Issue


class TestSupervisorA2AExecutor:
    """Test cases for SupervisorA2AExecutor."""
    
    @pytest.fixture
    def mock_supervisor_agent(self):
        """Create a mock supervisor agent."""
        agent = Mock()
        agent.name = "Supervisor"
        agent.id = "supervisor-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_supervisor_agent):
        """Create an executor instance with mock agent."""
        return SupervisorA2AExecutor(mock_supervisor_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid supervisor input data."""
        return {
            "user_prompt": "Build a REST API for task management",
            "project_directory": "/path/to/project",
            "project_id": 123,
            "application_id": 456,
            "license_header": "# Copyright 2025",
            "license_url": "https://example.com/license"
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
        assert isinstance(result, SupervisorInput)
        assert result.user_prompt == "Build a REST API for task management"
        assert result.project_directory == "/path/to/project"
        assert result.project_id == 123
        assert result.application_id == 456
        assert result.license_header == "# Copyright 2025"
        assert result.license_url == "https://example.com/license"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_user_prompt(self, executor):
        """Test input extraction with missing user_prompt."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "project_directory": "/path/to/project",
                    "project_id": 123,
                    "application_id": 456,
                    "license_header": "# Copyright 2025",
                    "license_url": "https://example.com/license"
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "Field required" in str(exc_info.value) and "user_prompt" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_project_directory(self, executor):
        """Test input extraction with missing project_directory."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Build a REST API",
                    "project_id": 123,
                    "application_id": 456,
                    "license_header": "# Copyright 2025",
                    "license_url": "https://example.com/license"
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "Field required" in str(exc_info.value) and "project_directory" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_project_id(self, executor):
        """Test input extraction with missing project_id."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Build a REST API",
                    "project_directory": "/path/to/project",
                    "application_id": 456,
                    "license_header": "# Copyright 2025",
                    "license_url": "https://example.com/license"
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "Field required" in str(exc_info.value) and "project_id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_supervisor_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required SupervisorOutput fields
        mock_output = {
            "application_name": "Task Management API",
            "project_status": PStatus.DONE.value,
            "agents_status": "All agents completed successfully",
            "current_task": {"id": "task-1", "name": "Setup project"},
            "current_planned_task": {"id": "planned-1", "name": "Create API endpoints"},
            "current_issue": {"id": "issue-1", "name": "Fix authentication"},
            "current_planned_issue": {"is_function_generation_required": False},
            "issues": {"items": []},
            "tasks": {"items": [
                {"id": "task-1", "name": "Setup project"},
                {"id": "task-2", "name": "Create models"}
            ]},
            "human_feedback": {},
            "functions_skeleton": {},
            "test_code": {},
            "planned_tasks": {"items": []},
            "planned_issues": {"items": []},
            "requirements_document": {},
            "code_generation_plan_list": [],
            "chat_history": []
        }
        
        mock_supervisor_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = SupervisorInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, SupervisorOutput)
        assert result.application_name == "Task Management API"
        assert result.project_status == PStatus.DONE
        assert result.agents_status == "All agents completed successfully"
        assert len(result.tasks.items) == 2
        
        # Verify the mock was called with correct state
        mock_supervisor_agent.graph.invoke.assert_called_once()
        call_args = mock_supervisor_agent.graph.invoke.call_args[0][0]
        assert call_args["user_prompt"] == valid_input["user_prompt"]
        assert call_args["project_directory"] == valid_input["project_directory"]
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_supervisor_agent, valid_input):
        """Test agent execution failure."""
        mock_supervisor_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = SupervisorInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Supervisor execution failed" in str(exc_info.value)
        assert "Graph execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response(self, executor):
        """Test response formatting with tasks and issues."""
        # Create mock output with tasks and issues
        output = SupervisorOutput(
            application_name="Task Management API",
            project_status=PStatus.DONE,
            agents_status="All agents completed",
            tasks=TaskQueue(items=[
                Task(id="task-1", name="Setup project"),
                Task(id="task-2", name="Create models")
            ]),
            issues=IssuesQueue(items=[
                Issue(id="issue-1", name="Fix authentication"),
                Issue(id="issue-2", name="Add validation")
            ])
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent message was sent twice (summary + data)
        assert updater.new_agent_message.call_count == 2
        
        # Check that the data message (second call) contains agent output
        call_args_list = updater.new_agent_message.call_args_list
        # Second call should contain the data part with agent_output
        data_parts = call_args_list[1][0][0]  # First positional arg (list of parts)
        data_part = data_parts[0]  # First part in the list
        assert hasattr(data_part, 'root')
        assert hasattr(data_part.root, 'data')
        assert "agent_output" in data_part.root.data
        
        # Verify artifacts were added
        assert updater.add_artifact.call_count == 2
        artifact_calls = updater.add_artifact.call_args_list
        
        # Verify tasks artifact
        tasks_artifact = artifact_calls[0][1]
        assert tasks_artifact["name"] == "Generated Tasks"
        assert tasks_artifact["artifact_id"] == "generated-tasks"
        
        # Verify issues artifact
        issues_artifact = artifact_calls[1][1]
        assert issues_artifact["name"] == "Identified Issues"
        assert issues_artifact["artifact_id"] == "identified-issues"
    
    @pytest.mark.asyncio
    async def test_format_response_no_artifacts(self, executor):
        """Test response formatting without tasks or issues."""
        # Create output without tasks or issues
        output = SupervisorOutput(
            application_name="Simple App",
            project_status=PStatus.DONE,
            agents_status="Completed"
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent message was sent twice (summary + data)
        assert updater.new_agent_message.call_count == 2
        
        # Verify no artifacts were added (empty tasks/issues)
        updater.add_artifact.assert_not_called()


class TestSupervisorAgentCardBuilder:
    """Test cases for SupervisorAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = SupervisorAgentCardBuilder("Supervisor", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "agent-orchestration"
        assert skills[0].name == "Agent Orchestration"
        assert "orchestration" in skills[0].tags
        
        assert skills[1].id == "project-management"
        assert skills[1].name == "Project Management"
        assert "project" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = SupervisorAgentCardBuilder("Supervisor", "1.0.0")
        card = (builder
                .with_description("Test supervisor agent")
                .with_url("http://localhost:8005/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod Supervisor Agent"
        assert card.description == "Test supervisor agent"
        assert card.url == "http://localhost:8005/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.supervisor.supervisor_a2a_server import create_supervisor_a2a_app
    
    # Mock dependencies
    with patch('agents.supervisor.supervisor_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.supervisor.supervisor_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8005,
                description="Test supervisor agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Supervisor"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_supervisor_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Supervisor Agent (A2A)"
            assert app.description == "Test supervisor agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes
            
            # Note: RPC endpoint is handled at the A2A server level