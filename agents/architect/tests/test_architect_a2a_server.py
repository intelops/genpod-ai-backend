"""
Test suite for Architect A2A server.

Tests the A2A protocol implementation for the Architect agent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import uuid

from a2a.types import Message, DataPart, TextPart, Part, TaskState
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

from agents.architect.architect_a2a_server import ArchitectA2AExecutor, ArchitectAgentCardBuilder
from agents.architect._internal.architect_state import ArchitectInput, ArchitectOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models import Task as GenPodTask, TaskQueue, RequirementsDocument, Status
from models.constants import ChatRoles


class TestArchitectA2AExecutor:
    """Test cases for ArchitectA2AExecutor."""
    
    @pytest.fixture
    def mock_architect_agent(self):
        """Create a mock architect agent."""
        agent = Mock()
        agent.name = "Architect"
        agent.id = "architect-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})  # Synchronous mock since it's called via asyncio.to_thread
        return agent
    
    @pytest.fixture
    def executor(self, mock_architect_agent):
        """Create an executor instance with mock agent."""
        return ArchitectA2AExecutor(mock_architect_agent)
    
    @pytest.fixture
    def valid_architect_input(self):
        """Create valid architect input data."""
        return {
            "user_prompt": "Design a REST API for task management",
            "project_status": "INITIAL",
            "project_directory": "/tmp/test-project",
            "current_task": {
                "task_id": "task-001",
                "task_status": "NEW",
                "description": "Design the architecture"
            },
            "chat_history": [
                ["user", "Create a task management system"]
            ],
            "additional_information": "Support team collaboration",
            "requested_standards": "Follow RESTful conventions",
            "license_header": "# Copyright 2024"
        }
    
    @pytest.fixture
    def valid_message(self, valid_architect_input):
        """Create a valid A2A message with architect input."""
        return Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": valid_architect_input}))
            ]
        )
    
    @pytest.mark.asyncio
    async def test_extract_input_success(self, executor, valid_message):
        """Test successful input extraction."""
        result = await executor._extract_input(valid_message)
        
        assert isinstance(result, ArchitectInput)
        assert result.user_prompt == "Design a REST API for task management"
        assert result.project_directory == "/tmp/test-project"
        assert result.current_task.task_id == "task-001"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_agent_input(self, executor):
        """Test input extraction with missing agent_input field."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[Part(root=TextPart(text="Hello"))]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "No agent_input found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_invalid_data(self, executor):
        """Test input extraction with invalid data."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {"invalid": "data"}}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError):
            await executor._extract_input(message)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_required_fields(self, executor):
        """Test input extraction with missing required fields."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "project_directory": "/tmp/test"
                    # Missing user_prompt
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "user_prompt" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_architect_agent, valid_architect_input):
        """Test successful agent execution."""
        # Setup mock response
        mock_output = {
            "current_task": valid_architect_input["current_task"],
            "chat_history": valid_architect_input["chat_history"],
            "project_name": "TaskManagementAPI",
            "tasks": TaskQueue(items=[
                GenPodTask(
                    task_id="task-001",
                    task_status=Status.NEW,
                    description="### Task 1: Setup API structure"
                )
            ]),
            "requirements_document": RequirementsDocument(
                project_summary="Task management REST API",
                tech_stack="Python, FastAPI",
                system_architecture="RESTful microservice",
                file_structure="Standard Python structure",
                microservice_design="Single service",
                tasks_summary="API development tasks",
                code_standards="PEP8",
                implementation_plan="Iterative development",
                license_terms="MIT"
            ),
        }
        
        mock_architect_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = ArchitectInput(**valid_architect_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, ArchitectOutput)
        assert result.project_name == "TaskManagementAPI"
        assert len(result.tasks.items) == 1
        assert result.requirements_document.project_summary == "Task management REST API"
        
        
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_architect_agent, valid_architect_input):
        """Test agent execution failure."""
        mock_architect_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = ArchitectInput(**valid_architect_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Architect execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response(self, executor):
        """Test response formatting."""
        # Create mock output
        output = ArchitectOutput(
            current_task=GenPodTask(task_id="current", task_status=Status.NEW, description="Current task"),
            chat_history=[],
            project_name="TestProject",
            tasks=TaskQueue(items=[
                GenPodTask(task_id="1", task_status=Status.NEW, description="Task 1"),
                GenPodTask(task_id="2", task_status=Status.NEW, description="Task 2")
            ]),
            requirements_document=RequirementsDocument(
                project_summary="Test project",
                tech_stack="Python",
                system_architecture="Monolithic",
                file_structure="Standard",
                microservice_design="N/A",
                tasks_summary="2 tasks",
                code_standards="PEP8",
                implementation_plan="Sequential",
                license_terms="MIT"
            )
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify summary was sent
        assert updater.update_status.call_count >= 1
        
        # Verify artifacts were added
        assert updater.add_artifact.call_count == 2  # Requirements doc + tasks
        
        # Check artifact calls
        artifact_calls = updater.add_artifact.call_args_list
        artifact_names = [call.kwargs.get('name') for call in artifact_calls]
        assert "Requirements Document" in artifact_names
        assert "Project Tasks" in artifact_names


class TestArchitectAgentCardBuilder:
    """Test cases for ArchitectAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = ArchitectAgentCardBuilder("Architect", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 1
        assert skills[0].id == "project-architecture"
        assert skills[0].name == "Project Architecture Design"
        assert "architecture" in skills[0].tags
        
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = ArchitectAgentCardBuilder("Architect", "1.0.0")
        card = (builder
                .with_description("Test architect agent")
                .with_url("http://localhost:8001")
                .with_capabilities(streaming=True)
                .build())
        
        assert card.name == "GenPod Architect Agent"
        assert card.description == "Test architect agent"
        assert card.url == "http://localhost:8001"
        assert card.capabilities.streaming is True
        assert len(card.skills) == 1
        
    def test_build_card_without_url_raises(self):
        """Test that building without URL raises error."""
        builder = ArchitectAgentCardBuilder("Architect", "1.0.0")
        
        with pytest.raises(ValueError) as exc_info:
            builder.build()
            
        assert "Agent URL must be set" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_architect_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.architect.architect_a2a_server import create_architect_a2a_app
    
    # Mock dependencies
    with patch('agents.architect.architect_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.architect.architect_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8001,
                description="Test architect"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Architect"
            
            # Create app
            app = create_architect_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Architect Agent (A2A)"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes
