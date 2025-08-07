"""
Test suite for Reviewer A2A server implementation.

Tests the A2A protocol wrapper for the Reviewer agent, including:
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
from agents.reviewer.reviewer_a2a_server import ReviewerA2AExecutor, ReviewerAgentCardBuilder
from agents.reviewer._internal.reviewer_state import ReviewerInput, ReviewerOutput
from core.a2a.exceptions import A2AInputExtractionError, A2AExecutionError
from models.models import RequirementsDocument, IssuesQueue, Issue


class TestReviewerA2AExecutor:
    """Test cases for ReviewerA2AExecutor."""
    
    @pytest.fixture
    def mock_reviewer_agent(self):
        """Create a mock reviewer agent."""
        agent = Mock()
        agent.name = "Reviewer"
        agent.id = "reviewer-001"
        agent.graph = Mock()
        agent.graph.invoke = Mock(return_value={})  # Synchronous mock since it's called via asyncio.to_thread
        return agent
    
    @pytest.fixture
    def executor(self, mock_reviewer_agent):
        """Create an executor instance with mock agent."""
        return ReviewerA2AExecutor(mock_reviewer_agent)
    
    @pytest.fixture
    def valid_input(self):
        """Create valid reviewer input data."""
        return {
            # Required BaseInputState fields
            "user_prompt": "Review the task management API project for code quality and security issues",
            "project_status": "REVIEWING",
            "project_directory": "/tmp/task_management_api",
            "current_task": {
                "task_id": "review-task-001",
                "task_status": "NEW",
                "description": "Code review and quality assessment task"
            },
            "chat_history": [["user", "Please review this project"], ["assistant", "I'll perform a comprehensive code review"]],
            
            # ReviewerInput specific fields
            "project_name": "Task Management API",
            "license_header": "# Copyright 2025 Test Company\n# MIT License",
            "requirements_document": {
                "project_summary": "Task management API with user authentication",
                "tech_stack": "Python, FastAPI, SQLAlchemy, PostgreSQL, JWT",
                "system_architecture": "RESTful API with microservices architecture",
                "file_structure": "app/, models/, routes/, tests/, migrations/",
                "microservice_design": "Authentication service, Task service, User service",
                "tasks_summary": "User management, task CRUD operations, authentication",
                "code_standards": "PEP 8, type hints, docstrings, comprehensive testing",
                "implementation_plan": "Phase 1: Core API, Phase 2: Advanced features",
                "license_terms": "MIT License with commercial use allowed"
            },
            "previous_issues": {
                "items": [
                    {"issue_id": "prev-1", "issue_status": "DONE", "description": "Previous security vulnerability fixed", "file_path": "/app/auth.py"}
                ]
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
        assert isinstance(result, ReviewerInput)
        assert result.project_name == "Task Management API"
        assert result.license_header == "# Copyright 2025 Test Company\n# MIT License"
        assert isinstance(result.requirements_document, RequirementsDocument)
        assert result.requirements_document.project_summary == "Task management API with user authentication"
        assert isinstance(result.previous_issues, IssuesQueue)
        assert len(result.previous_issues.items) == 1
        assert result.previous_issues.items[0].description == "Previous security vulnerability fixed"
    
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
                    "license_header": "# Copyright 2025",
                    "requirements_document": {
                        "project_summary": "Test project",
                        "tech_stack": "Python",
                        "system_architecture": "Test architecture",
                        "file_structure": "app/",
                        "microservice_design": "Single service",
                        "tasks_summary": "Test tasks",
                        "code_standards": "PEP 8",
                        "implementation_plan": "Test plan",
                        "license_terms": "MIT"
                    },
                    "previous_issues": {"items": []}
                    # Missing project_name
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "project_name" in str(exc_info.value)
    
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
                    "license_header": "# Copyright 2025",
                    "previous_issues": {"items": []}
                    # Missing requirements_document
                }}))
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            await executor._extract_input(message)
        
        assert "requirements_document" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_reviewer_agent, valid_input):
        """Test successful agent execution."""
        # Setup mock response with all required ReviewerOutput fields
        mock_output = {
            "current_task": valid_input["current_task"],
            "chat_history": valid_input["chat_history"],
            "issues": {
                "items": [
                    {"issue_id": "issue-1", "issue_status": "NEW", "description": "SQL injection risk in login", "file_path": "/app/auth.py"},
                    {"issue_id": "issue-2", "issue_status": "NEW", "description": "Missing error handling", "file_path": "/app/handlers.py"}
                ]
            }
        }
        
        mock_reviewer_agent.graph.invoke.return_value = mock_output
        
        # Execute
        input_obj = ReviewerInput(**valid_input)
        result = await executor._execute_agent(input_obj, "task-123")
        
        # Verify
        assert isinstance(result, ReviewerOutput)
        assert isinstance(result.issues, IssuesQueue)
        assert len(result.issues.items) == 2
        assert result.issues.items[0].description == "SQL injection risk in login"
        assert result.issues.items[1].description == "Missing error handling"
        
        # Verify the mock was called with correct state
        mock_reviewer_agent.graph.invoke.assert_called_once()
        call_args = mock_reviewer_agent.graph.invoke.call_args[0][0]
        assert call_args["project_name"] == valid_input["project_name"]
        assert "requirements_document" in call_args
    
    @pytest.mark.asyncio
    async def test_execute_agent_failure(self, executor, mock_reviewer_agent, valid_input):
        """Test agent execution failure."""
        mock_reviewer_agent.graph.invoke.side_effect = Exception("Graph execution failed")
        
        input_obj = ReviewerInput(**valid_input)
        
        with pytest.raises(A2AExecutionError) as exc_info:
            await executor._execute_agent(input_obj, "task-123")
        
        assert "Reviewer execution failed" in str(exc_info.value)
        assert "Graph execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_format_response_with_issues(self, executor):
        """Test response formatting with review issues."""
        from models.models import Task
        # Create mock output with issues
        output = ReviewerOutput(
            current_task=Task(task_id="current-task", task_status="NEW", description="Current task"),
            chat_history=[],
            issues=IssuesQueue(items=[
                Issue(issue_id="issue-1", issue_status="NEW", description="SQL injection risk", file_path="/app/auth.py"),
                Issue(issue_id="issue-2", issue_status="NEW", description="Slow database query", file_path="/app/db.py")
            ])
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
        
        # Verify artifact was added for issues
        updater.add_artifact.assert_called_once()
        artifact_call = updater.add_artifact.call_args[1]
        assert artifact_call["name"] == "Review Issues"
        assert artifact_call["artifact_id"] == "review-issues"
    
    @pytest.mark.asyncio
    async def test_format_response_no_issues(self, executor):
        """Test response formatting without issues (clean review)."""
        from models.models import Task
        # Create output without issues
        output = ReviewerOutput(
            current_task=Task(task_id="current-task", task_status="NEW", description="Current task"),
            chat_history=[],
            issues=IssuesQueue(items=[])
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
        
        # Verify no artifacts were added (no issues found)
        updater.add_artifact.assert_not_called()


class TestReviewerAgentCardBuilder:
    """Test cases for ReviewerAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test that default skills are properly defined."""
        builder = ReviewerAgentCardBuilder("Reviewer", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 2
        assert skills[0].id == "code-review"
        assert skills[0].name == "Code Review"
        assert "review" in skills[0].tags
        assert "quality" in skills[0].tags
        
        assert skills[1].id == "documentation-review"
        assert skills[1].name == "Documentation Review"
        assert "documentation" in skills[1].tags
    
    def test_build_card(self):
        """Test building a complete agent card."""
        builder = ReviewerAgentCardBuilder("Reviewer", "1.0.0")
        card = (builder
                .with_description("Test reviewer agent")
                .with_url("http://localhost:8006/")
                .with_capabilities(streaming=True, push_notifications=False)
                .build())
        
        assert card.name == "GenPod Reviewer Agent"
        assert card.description == "Test reviewer agent"
        assert card.url == "http://localhost:8006/"
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert len(card.skills) == 2


@pytest.mark.asyncio
async def test_create_a2a_app():
    """Test creating the A2A FastAPI application."""
    from agents.reviewer.reviewer_a2a_server import create_reviewer_a2a_app
    
    # Mock dependencies
    with patch('agents.reviewer.reviewer_a2a_server.A2AConfigLoader') as mock_loader:
        with patch('agents.reviewer.reviewer_a2a_server.DatabaseTaskStore') as mock_store:
            # Setup mock config
            mock_config = Mock()
            mock_config.get_agent_config.return_value = Mock(
                enabled=True,
                host="0.0.0.0",
                port=8006,
                description="Test reviewer agent"
            )
            mock_loader.return_value.load.return_value = mock_config
            
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "Reviewer"
            mock_agent.graph = Mock()
            mock_agent.graph.invoke = AsyncMock(return_value={})
            
            # Create app
            app = create_reviewer_a2a_app(mock_agent, "/tmp/test.db")
            
            # Verify app was created
            assert app is not None
            assert app.title == "GenPod Reviewer Agent (A2A)"
            assert app.description == "Test reviewer agent"
            
            # Verify health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/health" in routes