"""
Test suite for A2A utilities.

Tests the MessageExtractor and ResponseFormatter utility classes.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from a2a.types import Message, DataPart, TextPart, Part
from a2a.server.tasks.task_updater import TaskUpdater

from core.a2a.utils import MessageExtractor, ResponseFormatter
from core.a2a.exceptions import A2AInputExtractionError


# Test models
class MockInput(BaseModel):
    """Test input model."""
    required_field: str
    optional_field: str = "default"
    number_field: int = 42


class MockOutput(BaseModel):
    """Test output model."""
    result: str
    details: Dict[str, Any] = Field(default_factory=dict)
    items: List[str] = Field(default_factory=list)


class TestMessageExtractor:
    """Test suite for MessageExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a MessageExtractor instance."""
        return MessageExtractor()
    
    def test_extract_agent_input_success(self, extractor):
        """Test successful extraction of agent input."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={
                    "agent_input": {
                        "required_field": "test value",
                        "number_field": 100
                    }
                }))
            ]
        )
        
        result = extractor.extract_agent_input(
            message=message,
            input_model=MockInput,
            field_name="agent_input"
        )
        
        assert isinstance(result, MockInput)
        assert result.required_field == "test value"
        assert result.number_field == 100
        assert result.optional_field == "default"
    
    def test_extract_agent_input_no_message(self, extractor):
        """Test extraction with no message."""
        with pytest.raises(A2AInputExtractionError) as exc_info:
            extractor.extract_agent_input(
                message=None,
                input_model=MockInput,
                field_name="agent_input"
            )
        
        assert "Message is required" in str(exc_info.value)
    
    def test_extract_agent_input_no_data_parts(self, extractor):
        """Test extraction with no data parts."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=TextPart(text="Hello"))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            extractor.extract_agent_input(
                message=message,
                input_model=MockInput,
                field_name="agent_input"
            )
        
        assert "No agent_input found" in str(exc_info.value)
    
    def test_extract_agent_input_missing_field(self, extractor):
        """Test extraction when specified field is missing."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={
                    "other_field": {"data": "value"}
                }))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            extractor.extract_agent_input(
                message=message,
                input_model=MockInput,
                field_name="agent_input"
            )
        
        assert "No agent_input found" in str(exc_info.value)
    
    def test_extract_agent_input_invalid_data(self, extractor):
        """Test extraction with invalid data for model."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={
                    "agent_input": {
                        # Missing required_field
                        "number_field": "not a number"  # Wrong type
                    }
                }))
            ]
        )
        
        with pytest.raises(A2AInputExtractionError) as exc_info:
            extractor.extract_agent_input(
                message=message,
                input_model=MockInput,
                field_name="agent_input"
            )
        
        assert "Invalid agent_input" in str(exc_info.value)
    
    def test_extract_agent_input_multiple_data_parts(self, extractor):
        """Test extraction uses first matching data part."""
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={
                    "other_field": {"data": "first"}
                })),
                Part(root=DataPart(data={
                    "agent_input": {
                        "required_field": "correct value"
                    }
                })),
                Part(root=DataPart(data={
                    "agent_input": {
                        "required_field": "should not use this"
                    }
                }))
            ]
        )
        
        result = extractor.extract_agent_input(
            message=message,
            input_model=MockInput,
            field_name="agent_input"
        )
        
        assert result.required_field == "correct value"


class TestResponseFormatter:
    """Test suite for ResponseFormatter."""
    
    @pytest.fixture
    def formatter(self):
        """Create a ResponseFormatter instance."""
        return ResponseFormatter()
    
    @pytest.fixture
    def mock_updater(self):
        """Create a mock TaskUpdater."""
        updater = Mock(spec=TaskUpdater)
        updater.update_status = AsyncMock()
        updater.add_artifact = AsyncMock()
        updater.new_agent_message = Mock(return_value=Mock(update=AsyncMock()))
        return updater
    
    def test_create_summary(self, formatter):
        """Test summary creation."""
        summary = formatter.create_summary(
            agent_name="TestAgent",
            action="completed testing",
            details={
                "tests_run": 10,
                "tests_passed": 9,
                "coverage": "95%"
            }
        )
        
        assert "TestAgent completed testing" in summary
        assert "tests_run: 10" in summary
        assert "tests_passed: 9" in summary
        assert "coverage: 95%" in summary
    
    def test_create_summary_no_details(self, formatter):
        """Test summary creation without details."""
        summary = formatter.create_summary(
            agent_name="TestAgent",
            action="completed testing"
        )
        
        assert summary == "TestAgent completed testing"
    
    def test_create_summary_with_none_values(self, formatter):
        """Test summary creation handles None values."""
        summary = formatter.create_summary(
            agent_name="TestAgent",
            action="completed testing",
            details={
                "result": "success",
                "error": None,
                "count": 0
            }
        )
        
        assert "result: success" in summary
        # None values are filtered out, so error should not be in summary
        assert "error: None" not in summary
        assert "count: 0" in summary
    
    @pytest.mark.asyncio
    async def test_send_agent_output(self, formatter, mock_updater):
        """Test sending agent output."""
        output = MockOutput(
            result="test completed",
            details={"key": "value"},
            items=["item1", "item2"]
        )
        
        await formatter.send_agent_output(
            updater=mock_updater,
            output_model=output,
            summary="Test summary",
            field_name="agent_output"
        )
        
        # Verify summary was sent (called twice - once for summary, once for data)
        assert mock_updater.update_status.call_count == 2
        
        # Verify message was created twice (summary + data)
        assert mock_updater.new_agent_message.call_count == 2
        
        # Check that new_agent_message was called
        assert mock_updater.new_agent_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_agent_output_custom_field(self, formatter, mock_updater):
        """Test sending agent output with custom field name."""
        output = MockOutput(result="custom test")
        
        await formatter.send_agent_output(
            updater=mock_updater,
            output_model=output,
            summary="Custom summary",
            field_name="custom_output"
        )
        
        # Check that new_agent_message was called
        assert mock_updater.new_agent_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_add_artifact(self, formatter, mock_updater):
        """Test adding an artifact."""
        artifact_data = {
            "content": "Test artifact content",
            "metadata": {"type": "test"}
        }
        
        await formatter.add_artifact(
            updater=mock_updater,
            data=artifact_data,
            name="Test Artifact",
            artifact_id="test-artifact-001"
        )
        
        mock_updater.add_artifact.assert_called_once_with(
            parts=[Part(root=DataPart(data=artifact_data))],
            name="Test Artifact",
            artifact_id="test-artifact-001"
        )
    
    @pytest.mark.asyncio
    async def test_add_artifact_with_pydantic_model(self, formatter, mock_updater):
        """Test adding an artifact with Pydantic model data."""
        artifact_data = MockOutput(
            result="artifact result",
            items=["a", "b", "c"]
        )
        
        await formatter.add_artifact(
            updater=mock_updater,
            data=artifact_data,
            name="Model Artifact",
            artifact_id="model-artifact-001"
        )
        
        # Verify the model was converted to dict and wrapped in Part
        call_args = mock_updater.add_artifact.call_args[1]
        assert "parts" in call_args
        part = call_args["parts"][0]
        assert isinstance(part, Part)
        assert part.root.data["result"] == "artifact result"
        assert part.root.data["items"] == ["a", "b", "c"]
    
    @pytest.mark.asyncio
    async def test_send_error(self, formatter, mock_updater):
        """Test sending error messages."""
        error = ValueError("Test error message")
        
        await formatter.send_error(mock_updater, error)
        
        mock_updater.failed.assert_called_once()
        # Verify the error message structure
        call_args = mock_updater.failed.call_args[1]
        assert "message" in call_args
    
    @pytest.mark.asyncio
    async def test_send_error_with_context(self, formatter, mock_updater):
        """Test sending error messages with context."""
        error = ValueError("Test error")
        
        await formatter.send_error(mock_updater, error, context="Agent execution")
        
        mock_updater.failed.assert_called_once()
        # Verify the error message structure includes context
        call_args = mock_updater.failed.call_args[1]
        assert "message" in call_args


class TestIntegration:
    """Integration tests for MessageExtractor and ResponseFormatter."""
    
    @pytest.mark.asyncio
    async def test_extract_and_format_flow(self):
        """Test complete flow of extraction and formatting."""
        extractor = MessageExtractor()
        formatter = ResponseFormatter()
        
        # Create input message
        message = Message(
            message_id="msg-001",
            role="user",
            parts=[
                Part(root=DataPart(data={
                    "agent_input": {
                        "required_field": "integration test"
                    }
                }))
            ]
        )
        
        # Extract input
        input_data = extractor.extract_agent_input(
            message=message,
            input_model=MockInput,
            field_name="agent_input"
        )
        
        assert input_data.required_field == "integration test"
        
        # Process (mock agent work)
        output_data = MockOutput(
            result=f"Processed: {input_data.required_field}",
            details={"input_number": input_data.number_field}
        )
        
        # Format and send response
        mock_updater = Mock(spec=TaskUpdater)
        mock_updater.update_status = AsyncMock()
        mock_updater.new_agent_message = Mock(return_value=Mock(update=AsyncMock()))
        
        summary = formatter.create_summary(
            agent_name="TestAgent",
            action="processed input",
            details={"result": output_data.result}
        )
        
        await formatter.send_agent_output(
            updater=mock_updater,
            output_model=output_data,
            summary=summary,
            field_name="agent_output"
        )
        
        # Verify complete flow
        assert mock_updater.update_status.called
        assert mock_updater.new_agent_message.called