"""
Test suite for Planner A2A server implementation.

Tests the A2A protocol wrapper for the Planner agent, including:
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
from agents.planner.planner_a2a_server import PlannerA2AExecutor, PlannerAgentCardBuilder
from agents.planner._internal.planner_state import PlannerInput, PlannerOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.models import TaskQueue, IssuesQueue, RequirementsDocument, Issue, PlannedTaskQueue, PlannedIssuesQueue, Task, PlannedTask, PlannedIssue


class TestPlannerA2AExecutor:
    """Test cases for PlannerA2AExecutor."""
    
    @pytest.fixture
    def mock_planner_agent(self):
        """Create a mock planner agent."""
        agent = Mock()
        agent.name = "Planner"
        agent.id = "planner-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})  # Synchronous mock since it's called via asyncio.to_thread
        return agent
    
    @pytest.fixture
    def executor(self, mock_planner_agent):
        """Create an executor instance with mock agent."""
        return PlannerA2AExecutor(mock_planner_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid planner input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Create a user authentication system with secure login/logout functionality",
            "project_status": "NEW",
            "project_directory": "/tmp/test_project",
            "current_task": {
                "task_id": "task-main-001",
                "task_status": "NEW",
                "description": "Main task for authentication system development"
            },
            "chat_history": [["user", "Please create an authentication system"], ["assistant", "I'll help you create a secure authentication system"]],
            
            # PlannerInput specific fields
            "deliverable_list": {
                "items": [
                    {"task_id": "task-1", "task_status": "NEW", "description": "Create user authentication endpoints"},
                    {"task_id": "task-2", "task_status": "NEW", "description": "Setup database schema for users"}
                ]
            },
            "issue_list": {
                "items": [
                    {"issue_id": "issue-1", "issue_status": "NEW", "description": "Security vulnerability in authentication", "file_path": "/app/auth.py"}
                ]
            },
            "requirements_document": {
                "project_summary": "Web application with user authentication system",
                "tech_stack": "Python, FastAPI, SQLAlchemy, PostgreSQL",
                "system_architecture": "RESTful API with JWT authentication",
                "file_structure": "Standard Python project structure with app, models, routes",
                "microservice_design": "Single authentication microservice",
                "tasks_summary": "User registration, login, logout, session management",
                "code_standards": "PEP 8, type hints, comprehensive testing",
                "implementation_plan": "Phase 1: Basic auth, Phase 2: Advanced features", 
                "license_terms": "MIT License"
            },
            "human_feedback": "Focus on security best practices and use modern JWT tokens",
            "additional_information": "Consider using OAuth2 flow and password hashing with bcrypt",
            "current_issue": {"issue_id": "current-1", "issue_status": "NEW", "description": "Current focus on authentication security"}
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
        assert isinstance(result, PlannerInput)
        assert isinstance(result.deliverable_list, TaskQueue)
        assert len(result.deliverable_list.items) == 2
        assert result.deliverable_list.items[0].description == "Create user authentication endpoints"
        assert isinstance(result.issue_list, IssuesQueue)
        assert len(result.issue_list.items) == 1
        assert result.issue_list.items[0].description == "Security vulnerability in authentication"
        assert isinstance(result.requirements_document, RequirementsDocument)
        assert result.requirements_document.project_summary == "Web application with user authentication system"
        assert result.human_feedback == "Focus on security best practices and use modern JWT tokens"
        assert result.additional_information == "Consider using OAuth2 flow and password hashing with bcrypt"
    
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
                    "deliverable_list": {"items": []},
                    "issue_list": {"items": []},
                    "human_feedback": "Test feedback",
                    "additional_information": "Test info",
                    "current_issue": {"issue_id": "test-issue", "issue_status": "NEW", "description": "Test issue"}
                    # Missing requirements_document
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "requirements_document" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_planner_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required PlannerOutput fields
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "planned_tasks": {
                "items": [
                    {"task_id": "planned-1", "task_status": "NEW", "description": "Create login/logout API"},
                    {"task_id": "planned-2", "task_status": "NEW", "description": "Create user table schema"}
                ]
            },
            "planned_issues": {
                "items": [
                    {"id": "planned-issue-1", "status": "NEW", "description": "Review auth implementation", "is_function_generation_required": True}
                ]
            },
            "current_issue": {"issue_id": "current-1", "issue_status": "NEW", "description": "Active issue"},
            "deliverable_list": valid_input["deliverable_list"],
            "issue_list": valid_input["issue_list"]
        }
        
        mock_planner_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = PlannerInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, PlannerOutput)
        assert isinstance(result.planned_tasks, PlannedTaskQueue)
        assert len(result.planned_tasks.items) == 2
        assert result.planned_tasks.items[0].description == "Create login/logout API"
        assert isinstance(result.planned_issues, PlannedIssuesQueue)
        assert len(result.planned_issues.items) == 1
        assert result.planned_issues.items[0].description == "Review auth implementation"
        
        # Verify the mock was called with correct state
        mock_planner_agent.graph.invoke.assert_called_once()
        call_args = mock_planner_agent.graph.invoke.call_args[0][0]
        assert "deliverable_list" in call_args
        assert "requirements_document" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_planner_agent, valid_input):
        """Test agent execution failure."""
        mock_planner_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = PlannerInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Planner execution failed" in str(exc_info.value)
        assert "Graph execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response(self, executor):
        """Test response formatting with planned tasks and issues."""
        from models.models import Task
        # Create mock output
        output = PlannerOutput(
            current_task=Task(task_id="current-task", task_status="NEW", description="Current task"),
            chat_history=[],
            planned_tasks=PlannedTaskQueue(items=[
                PlannedTask(task_id="planned-1", task_status="NEW", description="Create auth system"),
                PlannedTask(task_id="planned-2", task_status="NEW", description="Configure DB")
            ]),
            planned_issues=PlannedIssuesQueue(items=[
                PlannedIssue(id="planned-issue-1", status="NEW", description="Review implementation", is_function_generation_required=True)
            ]),
            current_issue=Issue(issue_id="current-1", issue_status="NEW", description="Active issue"),
            deliverable_list=TaskQueue(),
            issue_list=IssuesQueue()
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent messages were sent
        assert updater.new_agent_message.call_count == 2
        
        # Verify artifacts were added
        assert updater.add_artifact.call_count == 2
        artifact_calls = updater.add_artifact.call_args_list
        
        # Verify planned tasks artifact
        tasks_artifact = artifact_calls[0][1]
        assert tasks_artifact["name"] == "Planned Tasks"
        assert tasks_artifact["artifact_id"] == "planned-tasks"
        
        # Verify planned issues artifact
        issues_artifact = artifact_calls[1][1]
        assert issues_artifact["name"] == "Planned Issues"
        assert issues_artifact["artifact_id"] == "planned-issues"
    
    @pytest.mark.asyncio
    async def test_format_response_no_artifacts(self, executor):
        """Test response formatting without planned tasks or issues."""
        from models.models import Task
        # Create output without planned tasks or issues
        output = PlannerOutput(
            current_task=Task(task_id="current-task", task_status="NEW", description="Current task"),
            chat_history=[],
            current_issue=Issue(issue_id="current-1", issue_status="NEW", description="Active issue"),
            planned_tasks=PlannedTaskQueue(),
            planned_issues=PlannedIssuesQueue(),
            deliverable_list=TaskQueue(),
            issue_list=IssuesQueue()
        )
        
        # Create mock updater
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock())
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify agent messages were sent
        assert updater.new_agent_message.call_count == 2
        
        # Verify no artifacts were added (empty planned tasks/issues)
        updater.add_artifact.assert_not_called()


class TestPlannerAgentCardBuilder:
    """Test cases for PlannerAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = PlannerAgentCardBuilder("Planner", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "task-planning"
        assert skills[0].name == "Task Planning"
        assert "planning" in skills[0].tags
        
        assert skills[1].id == "issue-planning"
        assert skills[1].name == "Issue Planning"
        assert "issues" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = PlannerAgentCardBuilder("Planner", "1.0.0")
        card = (builder
                .with_description("Test planner agent")
                .with_url("http://localhost:8004/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod Planner Agent"
        assert card.description == "Test planner agent"
        assert card.url == "http://localhost:8004/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.planner.planner_a2a_server import create_planner_a2a_app
    
    # Mock dependencies
    with patch('agents.planner.planner_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.planner.planner_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8004,
                description="Test planner agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Planner"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = AsyncMock(return_value={})
            
            # Create app
            app = create_planner_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Planner Agent (A2A)"
            assert app.description == "Test planner agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes