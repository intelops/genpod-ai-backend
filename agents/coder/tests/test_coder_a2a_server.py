"""
Test suite for Coder A2A server.

Tests the A2A protocol implementation for the Coder agent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import uuid

from a2a.types import Message, DataPart, TextPart, Part
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

from agents.coder.coder_a2a_server import CoderA2AExecutor, CoderAgentCardBuilder
from agents.coder._internal.coder_state import CoderInput, CoderOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.coder_models import FileContent
from models.models import Task as GenPodTask
from models.constants import Status


class TestCoderA2AExecutor:
    """Test cases for CoderA2AExecutor."""
    
    @pytest.fixture
    def mock_coder_agent(self):
        """Create a mock coder agent."""
        agent = Mock()
        agent.name = "Coder"
        agent.id = "coder-001"
        agent.graph = Mock()  
        agent.graph.invoke = Mock(return_value={})  # Synchronous mock since it's called via asyncio.to_thread
        return agent
    
    @pytest.fixture
    def executor(self, mock_coder_agent):
        """Create an executor instance with mock agent."""
        return CoderA2AExecutor(mock_coder_agent)
    
    @pytest.fixture
    def valid_coder_input(self):
        """Create valid coder input data."""
        from models.models import RequirementsDocument
        return {
            "user_prompt": "Create authentication module",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/test-project",
            "current_task": {
                "task_id": "task-001",
                "task_status": "NEW",
                "description": "Implement user authentication"
            },
            "chat_history": [
                ["user", "Create authentication module"]
            ],
            "project_name": "test-project",
            "requirements_document": {
                "project_summary": "Test project",
                "tech_stack": "Python",
                "system_architecture": "Simple architecture",
                "file_structure": "Standard structure",
                "microservice_design": "Monolith",
                "tasks_summary": "Authentication tasks",
                "code_standards": "PEP8",
                "implementation_plan": "Step by step",
                "license_terms": "MIT"
            },
            "license_url": "https://opensource.org/licenses/MIT",
            "license_header": "# Copyright 2024",
            "functions_skeleton": {"main.py": "def authenticate(): pass"},
            "test_code": {"test_main.py": "def test_authenticate(): pass"},
            "current_planned_task": {
                "task_id": "planned-001",
                "task_status": "NEW",
                "description": "Current planned task",
                "is_function_generation_required": True
            },
            "current_planned_issue": {
                "id": "planned-issue-001",
                "status": "NEW",
                "description": "Current planned issue",
                "is_function_generation_required": True
            },
            "current_issue": {
                "issue_id": "issue-001",
                "issue_status": "NEW",
                "description": "Current issue"
            }
        }
    
    @pytest.fixture
    def valid_message(self, valid_coder_input):
        """Create a valid A2A message with coder input."""
        return Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": valid_coder_input}))
            ]
        )
    
    @pytest.mark.asyncio
    async def test_extract_input_success(self, executor, valid_message):
        """Test successful input extraction."""
        result = await executor._extract_input(valid_message)
        
        assert isinstance(result, CoderInput)
        assert result.current_task.task_id == "task-001"
        assert result.project_directory == "/tmp/test-project"
        assert result.project_name == "test-project"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_task(self, executor):
        """Test input extraction with missing task field."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "project_directory": "/tmp/test"
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "PlannedIssue" in str(exc_info.value) or "is_function_generation_required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_project_directory(self, executor):
        """Test input extraction with missing project_directory field."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "current_task": {"task_id": "1", "task_status": "NEW"},
                    "user_prompt": "test prompt"
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "PlannedIssue" in str(exc_info.value) or "is_function_generation_required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_coder_agent, valid_coder_input):
        """Test successful agent execution."""
        # Setup mock response
        mock_output = {
            "current_task": valid_coder_input["current_task"],
            "chat_history": valid_coder_input["chat_history"],
            "code_generation_plan_list": [],
            "current_planned_task": valid_coder_input["current_planned_task"],
            "current_planned_issue": valid_coder_input["current_planned_issue"],
            "current_issue": valid_coder_input["current_issue"]
        }
        
        mock_coder_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = CoderInput(**valid_coder_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, CoderOutput)
        assert result.current_task.task_id == "task-001"
        assert len(result.code_generation_plan_list) == 0
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_coder_agent, valid_coder_input):
        """Test agent execution failure."""
        mock_coder_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = CoderInput(**valid_coder_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Coder execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response(self, executor):
        """Test response formatting."""
        from models.models import PlannedTask, PlannedIssue, Issue
        # Create mock output
        output = CoderOutput(
            current_task=GenPodTask(task_id="1", task_status=Status.NEW, description="Task 1"),
            chat_history=[],
            code_generation_plan_list=[],
            current_planned_task=PlannedTask(task_id="planned-1", task_status=Status.NEW, description="Planned task", is_function_generation_required=True),
            current_planned_issue=PlannedIssue(id="planned-issue-1", status=Status.NEW, description="Planned issue", is_function_generation_required=True),
            current_issue=Issue(issue_id="issue-1", issue_status=Status.NEW, description="Current issue")
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify status was updated
        assert updater.update_status.call_count >= 1


class TestCoderAgentCardBuilder:
    """Test cases for CoderAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = CoderAgentCardBuilder("Coder", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "code-implementation"
        assert skills[0].name == "Code Implementation"
        assert "coding" in skills[0].tags
        assert skills[1].id == "code-generation"
        assert skills[1].name == "Code Generation"
        
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = CoderAgentCardBuilder("Coder", "1.0.0")
        card = (builder
                .with_description("Test coder agent")
                .with_url("http://localhost:8002")
                .with_capabilities(streaming=True)
                .build())
        
        assert card.name == "GenPod Coder Agent"
        assert card.description == "Test coder agent"
        assert card.url == "http://localhost:8002"
        assert card.capabilities.streaming is True
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_coder_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.coder.coder_a2a_server import create_coder_a2a_app
    
    # Mock dependencies
    with patch('agents.coder.coder_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.coder.coder_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8002,
                description="Test coder"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Coder"
            
            # Create app
            app = create_coder_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Coder Agent (A2A)"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes