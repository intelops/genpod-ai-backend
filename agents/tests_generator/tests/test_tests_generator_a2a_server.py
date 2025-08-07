"""
Test suite for Tests Generator A2A server implementation.

Tests the A2A protocol wrapper for the Tests Generator agent, including:
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
from agents.tests_generator.tests_generator_a2a_server import TestsGeneratorA2AExecutor, TestsGeneratorAgentCardBuilder
from agents.tests_generator._internal.tests_generator_state import TestCoderInput, TestCoderOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.models import RequirementsDocument, PlannedTask, PlannedIssue


class TestTestsGeneratorA2AExecutor:
    """Test cases for TestsGeneratorA2AExecutor."""
    
    @pytest.fixture
    def mock_tests_generator_agent(self):
        """Create a mock tests generator agent."""
        agent = Mock()
        agent.name = "TestsGenerator"
        agent.id = "tests_generator-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})
        return agent
    
    @pytest.fixture
    def executor(self, mock_tests_generator_agent):
        """Create an executor instance with mock agent."""
        return TestsGeneratorA2AExecutor(mock_tests_generator_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid tests generator input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Generate comprehensive unit tests for the authentication system",
            "project_status": "EXECUTING",
            "project_directory": "/tmp/task_management_api",
            "current_task": {
                "task_id": "test-gen-task-001",
                "task_status": "INPROGRESS",
                "description": "Generate unit tests for authentication components"
            },
            "chat_history": [["user", "Generate tests for auth system"], ["assistant", "I'll generate comprehensive unit tests"]],
            
            # TestCoderInput specific fields
            "project_name": "Task Management API",
            "requirements_document": {
                "project_summary": "Task management API with user authentication",
                "tech_stack": "Python, FastAPI, SQLAlchemy, PostgreSQL, pytest",
                "system_architecture": "RESTful API with JWT authentication",
                "file_structure": "app/, models/, routes/, tests/, conftest.py",
                "microservice_design": "Authentication service, Task service",
                "tasks_summary": "User authentication, task CRUD, session management",
                "code_standards": "PEP 8, type hints, pytest fixtures, 100% coverage",
                "implementation_plan": "TDD approach with comprehensive test suite",
                "license_terms": "MIT License"
            },
            "current_planned_task": {
                "parent_task_id": "parent-001",
                "task_id": "task-1",
                "task_status": "NEW",
                "is_function_generation_required": True,
                "is_test_code_generated": False,
                "is_code_generated": False,
                "description": "Implement user authentication endpoints with login/logout functionality"
            },
            "current_planned_issue": {
                "parent_id": "parent-issue-001",
                "id": "issue-1",
                "status": "NEW",
                "is_function_generation_required": True,
                "is_test_code_generated": False,
                "is_code_generated": False,
                "file_path": "/app/auth.py",
                "line_number": 42,
                "description": "Security vulnerability in authentication bypass that needs fixing",
                "suggestions": ["Add input validation", "Implement rate limiting", "Use secure session tokens"]
            }
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
        assert isinstance(result, TestCoderInput)
        assert result.project_name == "Task Management API"
        assert isinstance(result.requirements_document, RequirementsDocument)
        assert result.requirements_document.project_summary == "Task management API with user authentication"
        assert isinstance(result.current_planned_task, PlannedTask)
        assert result.current_planned_task.description == "Implement user authentication endpoints with login/logout functionality"
        assert isinstance(result.current_planned_issue, PlannedIssue)
        assert result.current_planned_issue.description == "Security vulnerability in authentication bypass that needs fixing"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_project_name(self, executor):
        """Test input extraction with missing project_name."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW",
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"},
                    "requirements_document": {
                        "project_summary": "Test project",
                        "tech_stack": "Python",
                        "system_architecture": "Test arch",
                        "file_structure": "app/",
                        "microservice_design": "Single service",
                        "tasks_summary": "Test tasks",
                        "code_standards": "PEP 8",
                        "implementation_plan": "Test plan",
                        "license_terms": "MIT"
                    },
                    "current_planned_task": {"task_id": "task-1", "task_status": "NEW", "description": "Test task", "is_function_generation_required": True},
                    "current_planned_issue": {"id": "issue-1", "status": "NEW", "description": "Test issue", "is_function_generation_required": True, "file_path": "/test/path", "line_number": 1, "suggestions": []}
                    # Missing project_name
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "project_name" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_requirements_document(self, executor):
        """Test input extraction with missing requirements_document."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={"agent_input": {
                    "user_prompt": "Test prompt",
                    "project_status": "NEW", 
                    "project_directory": "/tmp/test",
                    "current_task": {"task_id": "test-task", "task_status": "NEW", "description": "Test task"},
                    "project_name": "Test Project",
                    "current_planned_task": {"task_id": "task-1", "task_status": "NEW", "description": "Test task", "is_function_generation_required": True},
                    "current_planned_issue": {"id": "issue-1", "status": "NEW", "description": "Test issue", "is_function_generation_required": True, "file_path": "/test/path", "line_number": 1, "suggestions": []}
                    # Missing requirements_document
                }}))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            await executor._extract_input(message)
        
        assert "requirements_document" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_tests_generator_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required TestCoderOutput fields
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "current_planned_task": valid_input["current_planned_task"],
            "current_planned_issue": valid_input["current_planned_issue"],
            "test_code": {
                "test_auth.py": "import pytest\n\ndef test_login():\n    assert True",
                "test_user.py": "import pytest\n\ndef test_user_creation():\n    assert True"
            },
            "function_signatures": {
                "auth_service": {
                    "login": {"params": ["username", "password"], "returns": "User"},
                    "logout": {"params": ["user_id"], "returns": "bool"}
                }
            }
        }
        
        mock_tests_generator_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = TestCoderInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, TestCoderOutput)
        assert isinstance(result.current_planned_task, PlannedTask)
        assert result.current_planned_task.description == "Implement user authentication endpoints with login/logout functionality"
        assert isinstance(result.current_planned_issue, PlannedIssue)
        assert result.current_planned_issue.description == "Security vulnerability in authentication bypass that needs fixing"
        assert len(result.test_code) == 2
        assert "test_auth.py" in result.test_code
        assert "test_user.py" in result.test_code
        assert "auth_service" in result.function_signatures
        
        # Verify the mock was called with correct state
        mock_tests_generator_agent.graph.invoke.assert_called_once()
        call_args = mock_tests_generator_agent.graph.invoke.call_args[0][0]
        assert call_args["project_name"] == valid_input["project_name"]
        assert "requirements_document" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_tests_generator_agent, valid_input):
        """Test agent execution failure."""
        mock_tests_generator_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = TestCoderInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Tests Generator execution failed" in str(exc_info.value)
        assert "Graph execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_artifacts(self, executor):
        """Test response formatting with test code and function signatures."""
        # Create mock output with test code and function signatures
        from models.models import Task
        from models.constants import ChatRoles
        
        output = TestCoderOutput(
            current_task=Task(task_id="task-1", description="Test task"),
            chat_history=[(ChatRoles.USER, "test message")],
            current_planned_task=PlannedTask(task_id="task-1", description="Test task", is_function_generation_required=True),
            current_planned_issue=PlannedIssue(id="issue-1", description="Test issue", is_function_generation_required=True),
            test_code={
                "test_auth.py": "import pytest\n\ndef test_login():\n    assert True",
                "test_user.py": "import pytest\n\ndef test_user_creation():\n    assert True"
            },
            function_signatures={
                "auth_service": {
                    "login": {"params": ["username", "password"], "returns": "User"},
                    "logout": {"params": ["user_id"], "returns": "bool"}
                }
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
        
        # Verify artifacts were added
        assert updater.add_artifact.call_count == 2
        artifact_calls = updater.add_artifact.call_args_list
        
        # Verify test code artifact
        test_code_artifact = artifact_calls[0][1]
        assert test_code_artifact["name"] == "Generated Test Code"
        assert test_code_artifact["artifact_id"] == "test-code"
        
        # Verify function signatures artifact
        signatures_artifact = artifact_calls[1][1]
        assert signatures_artifact["name"] == "Function Signatures"
        assert signatures_artifact["artifact_id"] == "function-signatures"
    
    @pytest.mark.asyncio
    async def test_format_response_no_artifacts(self, executor):
        """Test response formatting without test code or function signatures."""
        # Create output without test code or function signatures
        from models.models import Task
        from models.constants import ChatRoles
        
        output = TestCoderOutput(
            current_task=Task(task_id="task-1", description="Test task"),
            chat_history=[(ChatRoles.USER, "test message")],
            current_planned_task=PlannedTask(task_id="task-1", description="Test task", is_function_generation_required=True),
            current_planned_issue=PlannedIssue(id="issue-1", description="Test issue", is_function_generation_required=True),
            test_code={},
            function_signatures={}
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
        
        # Verify no artifacts were added (empty test code and function signatures)
        updater.add_artifact.assert_not_called()


class TestTestsGeneratorAgentCardBuilder:
    """Test cases for TestsGeneratorAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = TestsGeneratorAgentCardBuilder("TestsGenerator", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "test-generation"
        assert skills[0].name == "Test Code Generation"
        assert "testing" in skills[0].tags
        assert "unit-tests" in skills[0].tags
        
        assert skills[1].id == "test-frameworks"
        assert skills[1].name == "Test Framework Support"
        assert "pytest" in skills[1].tags
        assert "testing-frameworks" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = TestsGeneratorAgentCardBuilder("TestsGenerator", "1.0.0")
        card = (builder
                .with_description("Test tests generator agent")
                .with_url("http://localhost:8007/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod TestsGenerator Agent"
        assert card.description == "Test tests generator agent"
        assert card.url == "http://localhost:8007/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.tests_generator.tests_generator_a2a_server import create_tests_generator_a2a_app
    
    # Mock dependencies
    with patch('agents.tests_generator.tests_generator_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.tests_generator.tests_generator_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8007,
                description="Test tests generator agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "TestsGenerator"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = Mock(return_value={})
            
            # Create app
            app = create_tests_generator_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Tests Generator Agent (A2A)"
            assert app.description == "Test tests generator agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes