"""
Test suite for BaseA2AExecutor.

Tests the base executor class that all agent executors inherit from.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional

from a2a.types import Message
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

from core.a2a.base.executor import BaseA2AExecutor


# Test implementation of BaseA2AExecutor
class MockExecutor(BaseA2AExecutor):
    """Concrete implementation for testing."""
    
    async def _extract_input(self, message: Optional[Message]):
        """Test implementation of input extraction."""
        if not message:
            raise ValueError("No message provided")
        return {"test": "input"}
    
    async def _execute_agent(self, agent_input, task_id: str):
        """Test implementation of agent execution."""
        if agent_input.get("fail"):
            raise Exception("Test failure")
        return {"test": "output", "task_id": task_id}
    
    async def _format_response(self, agent_output, updater: TaskUpdater):
        """Test implementation of response formatting."""
        await updater.update_status("Formatted response")
        if agent_output.get("artifacts"):
            for artifact in agent_output["artifacts"]:
                await updater.add_artifact(
                    data=artifact["data"],
                    name=artifact["name"],
                    artifact_id=artifact["id"]
                )


class TestBaseA2AExecutor:
    """Test suite for BaseA2AExecutor."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = Mock()
        agent.name = "TestAgent"
        agent.id = "test-agent-001"
        return agent
    
    @pytest.fixture
    def executor(self, mock_agent):
        """Create a test executor instance."""
        return MockExecutor(mock_agent, "TestAgent")
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock request context."""
        context = Mock(spec=RequestContext)
        context.request_id = "req-123"
        context.current_task = Mock(id="task-123", context_id="ctx-123")
        context.message = Message(
            message_id="msg-001",
            role="user",
            parts=[]
        )
        return context
    
    @pytest.fixture
    def mock_event_queue(self):
        """Create a mock event queue."""
        queue = Mock(spec=EventQueue)
        queue.put = AsyncMock()
        queue.enqueue_event = AsyncMock()
        return queue
    
    @pytest.mark.asyncio
    async def test_execute_success(self, executor, mock_context, mock_event_queue):
        """Test successful execution flow."""
        # Mock TaskUpdater
        with patch('core.a2a.base.executor.TaskUpdater') as mock_updater_class:
            mock_updater = Mock(spec=TaskUpdater)
            mock_updater.start_work = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater.update_status = AsyncMock()
            mock_updater_class.return_value = mock_updater
            
            # Execute
            await executor.execute(mock_context, mock_event_queue)
            
            # Verify task lifecycle
            mock_updater.start_work.assert_called_once()
            mock_updater.complete.assert_called_once()
            
            # Verify response was formatted
            mock_updater.update_status.assert_called_with("Formatted response")
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, executor, mock_context, mock_event_queue):
        """Test execution with error handling."""
        # Modify context to trigger error
        mock_context.message = None
        
        # Mock TaskUpdater
        with patch('core.a2a.base.executor.TaskUpdater') as mock_updater_class:
            mock_updater = Mock(spec=TaskUpdater)
            mock_updater.start_work = AsyncMock()
            mock_updater.failed = AsyncMock()
            mock_updater_class.return_value = mock_updater
            
            # Execute
            await executor.execute(mock_context, mock_event_queue)
            
            # Verify error was reported via failed method
            mock_updater.failed.assert_called_once()
            # Check that the error message contains the expected text
            call_args = mock_updater.failed.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_execute_agent_error(self, executor, mock_context, mock_event_queue):
        """Test handling of agent execution errors."""
        # Create message that will trigger agent error
        mock_context.message = Message(
            message_id="msg-001",
            role="user",
            parts=[]
        )
        
        # Override _extract_input to return failure trigger
        async def extract_fail(msg):
            return {"fail": True}
        
        executor._extract_input = extract_fail
        
        # Mock TaskUpdater
        with patch('core.a2a.base.executor.TaskUpdater') as mock_updater_class:
            mock_updater = Mock(spec=TaskUpdater)
            mock_updater.start_work = AsyncMock()
            mock_updater.failed = AsyncMock()
            mock_updater_class.return_value = mock_updater
            
            # Execute
            await executor.execute(mock_context, mock_event_queue)
            
            # Verify error was reported via failed method
            mock_updater.failed.assert_called_once()
            # Check that the error message contains the expected text
            call_args = mock_updater.failed.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_ensure_task_with_existing_task(self, executor, mock_context, mock_event_queue):
        """Test _ensure_task when context already has a task."""
        result = await executor._ensure_task(mock_context, mock_event_queue)
        
        assert result == mock_context.current_task
        assert result.id == "task-123"
    
    @pytest.mark.asyncio
    async def test_ensure_task_creates_new_task(self, executor, mock_event_queue):
        """Test _ensure_task when context has no task."""
        # Create context without task
        context = Mock(spec=RequestContext)
        context.request_id = "req-456"
        context.current_task = None
        context.task_id = "task-456"
        context.context_id = "ctx-456"
        context.message = None
        
        # Since there's no _create_task method, this will create a new Task
        result = await executor._ensure_task(context, mock_event_queue)
        
        # Should create a new task and publish it to event queue
        assert result is not None
        assert mock_event_queue.enqueue_event.called
    
    def test_agent_name(self, executor):
        """Test agent_name property."""
        assert executor.agent_name == "TestAgent"
    
    @pytest.mark.asyncio
    async def test_format_response_with_artifacts(self, executor):
        """Test response formatting with artifacts."""
        mock_updater = Mock(spec=TaskUpdater)
        mock_updater.update_status = AsyncMock()
        mock_updater.add_artifact = AsyncMock()
        
        output = {
            "test": "output",
            "artifacts": [
                {"data": {"content": "artifact1"}, "name": "Artifact 1", "id": "art-1"},
                {"data": {"content": "artifact2"}, "name": "Artifact 2", "id": "art-2"}
            ]
        }
        
        await executor._format_response(output, mock_updater)
        
        # Verify artifacts were added
        assert mock_updater.add_artifact.call_count == 2
        
        # Check artifact calls
        calls = mock_updater.add_artifact.call_args_list
        assert calls[0][1]["name"] == "Artifact 1"
        assert calls[0][1]["artifact_id"] == "art-1"
        assert calls[1][1]["name"] == "Artifact 2"
        assert calls[1][1]["artifact_id"] == "art-2"


class TestBaseA2AExecutorIntegration:
    """Integration tests for BaseA2AExecutor."""
    
    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test the complete execution flow with all components."""
        # Create real components
        agent = Mock(name="TestAgent", id="test-001")
        executor = MockExecutor(agent, "TestAgent")
        
        # Create context with message
        context = Mock(spec=RequestContext)
        context.request_id = "req-999"
        context.current_task = Mock(id="task-999", context_id="ctx-999")
        context.message = Message(
            message_id="msg-999",
            role="user",
            parts=[]
        )
        
        # Create event queue
        event_queue = Mock(spec=EventQueue)
        event_queue.put = AsyncMock()
        
        # Execute with mocked TaskUpdater
        with patch('core.a2a.base.executor.TaskUpdater') as mock_updater_class:
            # Track all method calls
            call_order = []
            
            mock_updater = Mock(spec=TaskUpdater)
            mock_updater.start_work = AsyncMock(side_effect=lambda: call_order.append("start_work"))
            mock_updater.complete = AsyncMock(side_effect=lambda: call_order.append("complete"))
            mock_updater.update_status = AsyncMock(side_effect=lambda x: call_order.append(f"update_status:{x}"))
            mock_updater.error = AsyncMock(side_effect=lambda x: call_order.append(f"error:{x}"))
            mock_updater_class.return_value = mock_updater
            
            # Execute
            await executor.execute(context, event_queue)
            
            # Verify execution order
            assert call_order == [
                "start_work",
                "update_status:Formatted response",
                "complete"
            ]
            
            # Verify TaskUpdater was created with correct params
            mock_updater_class.assert_called_once_with(
                event_queue,
                context.current_task.id,
                context.current_task.context_id
            )
