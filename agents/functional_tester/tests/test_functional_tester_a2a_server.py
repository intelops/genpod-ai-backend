"""
Unit tests for Functional Tester A2A Server
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from a2a.types import Message, Part, TextPart

from agents.functional_tester.functional_tester_agent import FunctionalTesterAgent
from agents.functional_tester.functional_tester_a2a_server import (
    FunctionalTesterA2AExecutor,
    FunctionalTesterAgentCardBuilder,
    create_functional_tester_a2a_app
)
from agents.functional_tester._internal.functional_tester_state import (
    FunctionalTesterInput,
    FunctionalTesterOutput,
    FunctionalTesterState
)
from models.models import RequirementsDocument, PlannedTask


class TestFunctionalTesterA2AExecutor:
    """Test cases for FunctionalTesterA2AExecutor."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock functional tester agent."""
        agent = Mock(spec=FunctionalTesterAgent)
        agent.graph = Mock()
        agent.graph.invoke = Mock()
        return agent
    
    @pytest.fixture
    def executor(self, mock_agent):
        """Create executor instance with mock agent."""
        return FunctionalTesterA2AExecutor(mock_agent)
    
    @pytest.mark.asyncio
    async def test_extract_input_valid(self, executor):
        """Test input extraction with valid message."""
        # Create test message
        message = Message(
            parts=[
                Part(
                    text=TextPart(
                        text='{"agent_input": {"project_name": "TestProject", "requirements_document": {"content": "Test requirements"}}}'
                    )
                )
            ]
        )
        
        # Extract input
        result = await executor._extract_input(message)
        
        # Verify
        assert isinstance(result, FunctionalTesterInput)
        assert result.project_name == "TestProject"
        assert result.requirements_document.content == "Test requirements"
    
    @pytest.mark.asyncio
    async def test_extract_input_missing_project_name(self, executor):
        """Test input extraction with missing project name."""
        message = Message(
            parts=[
                Part(
                    text=TextPart(
                        text='{"agent_input": {"requirements_document": {"content": "Test requirements"}}}'
                    )
                )
            ]
        )
        
        with pytest.raises(ValueError, match="project_name is required"):
            await executor._extract_input(message)
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, executor, mock_agent):
        """Test successful agent execution."""
        # Setup mock
        mock_output = {
            "project_name": "TestProject",
            "test_scenarios": {"feature1": [{"scenario": "test"}]},
            "functional_test_code": {"test_main.py": "def test_main(): pass"},
            "test_framework_config": {"framework": "pytest"}
        }
        mock_agent.graph.invoke.return_value = mock_output
        
        # Create input
        test_input = FunctionalTesterInput(
            project_name="TestProject",
            requirements_document=RequirementsDocument(content="Test requirements")
        )
        
        # Execute
        result = await executor._execute_agent(test_input, "task-123")
        
        # Verify
        assert isinstance(result, FunctionalTesterOutput)
        assert result.test_scenarios == {"feature1": [{"scenario": "test"}]}
        assert result.functional_test_code == {"test_main.py": "def test_main(): pass"}
        mock_agent.graph.invoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_format_response(self, executor):
        """Test response formatting."""
        # Create mock updater
        updater = AsyncMock()
        
        # Create output
        output = FunctionalTesterOutput(
            test_scenarios={"feature1": [{"scenario": "test"}]},
            functional_test_code={"test_main.py": "def test_main(): pass"},
            test_framework_config={"framework": "pytest"},
            current_planned_task=PlannedTask(task_id="task-123")
        )
        
        # Format response
        await executor._format_response(output, updater)
        
        # Verify formatter methods were called
        assert updater.add_message.called


class TestFunctionalTesterAgentCardBuilder:
    """Test cases for FunctionalTesterAgentCardBuilder."""
    
    def test_default_skills(self):
        """Test default skills definition."""
        builder = FunctionalTesterAgentCardBuilder("FunctionalTester", "1.0.0")
        skills = builder._default_skills()
        
        assert len(skills) == 3
        assert skills[0].id == "functional-test-generation"
        assert skills[1].id == "test-scenario-design"
        assert skills[2].id == "test-automation-frameworks"
    
    def test_build_agent_card(self):
        """Test building agent card."""
        builder = FunctionalTesterAgentCardBuilder("FunctionalTester", "1.0.0")
        card = builder.with_description("Test agent").build()
        
        assert card.name == "FunctionalTester"
        assert card.version == "1.0.0"
        assert card.description == "Test agent"
        assert len(card.skills) == 3


class TestCreateFunctionalTesterA2AApp:
    """Test cases for create_functional_tester_a2a_app function."""
    
    @patch('agents.functional_tester.functional_tester_a2a_server.A2AConfigLoader')
    @patch('agents.functional_tester.functional_tester_a2a_server.DatabaseTaskStore')
    def test_create_app_success(self, mock_task_store, mock_config_loader):
        """Test successful app creation."""
        # Setup mocks
        mock_config = Mock()
        mock_agent_config = Mock()
        mock_agent_config.enabled = True
        mock_agent_config.description = "Test Functional Tester"
        mock_agent_config.host = "localhost"
        mock_agent_config.port = 8011
        
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_config_loader.return_value.load.return_value = mock_config
        
        # Create mock agent
        mock_agent = Mock(spec=FunctionalTesterAgent)
        
        # Create app
        app = create_functional_tester_a2a_app(mock_agent, "test.db")
        
        # Verify
        assert isinstance(app, FastAPI)
        assert app.title == "GenPod Functional Tester Agent (A2A)"
        mock_task_store.assert_called_once_with("sqlite:///test.db")
    
    @patch('agents.functional_tester.functional_tester_a2a_server.A2AConfigLoader')
    def test_create_app_agent_disabled(self, mock_config_loader):
        """Test app creation when agent is disabled."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_agent_config.return_value = None
        mock_config_loader.return_value.load.return_value = mock_config
        
        # Create mock agent
        mock_agent = Mock(spec=FunctionalTesterAgent)
        
        # Attempt to create app
        with pytest.raises(ValueError, match="Functional Tester agent is not enabled"):
            create_functional_tester_a2a_app(mock_agent, "test.db")