"""
Utilities for formatting A2A responses.

Provides consistent response formatting across all agents.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TextPart, DataPart, TaskState
from core.a2a.exceptions import A2AOutputFormattingError
from utils.logger import logger

T = TypeVar('T', bound=BaseModel)


class ResponseFormatter:
    """
    Utility class for formatting A2A responses.
    
    Provides consistent methods for creating response messages
    and artifacts from agent outputs.
    """
    
    @staticmethod
    async def send_agent_output(
        updater: TaskUpdater,
        output_model: T,
        summary: str,
        field_name: str = "agent_output"
    ) -> None:
        """
        Send agent output as A2A response.
        
        Args:
            updater: Task updater for sending messages
            output_model: Pydantic model containing output
            summary: Human-readable summary of the output
            field_name: Name of the field for output data
        """
        try:
            # Send summary as text
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message(
                    [Part(root=TextPart(text=summary))]
                )
            )
            
            # Send complete output as data
            output_data = {field_name: output_model.model_dump()}
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message(
                    [Part(root=DataPart(data=output_data))]
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to format response: {e}")
            raise A2AOutputFormattingError(f"Failed to format response: {str(e)}")
    
    @staticmethod
    async def add_artifact(
        updater: TaskUpdater,
        data: Any,
        name: str,
        artifact_id: str,
        as_data: bool = True
    ) -> None:
        """
        Add an artifact to the task.
        
        Args:
            updater: Task updater for adding artifacts
            data: Data to include in artifact
            name: Human-readable name for the artifact
            artifact_id: Unique identifier for the artifact
            as_data: If True, wrap in DataPart; if False, wrap in TextPart
        """
        try:
            if as_data:
                # Convert to dict if it's a Pydantic model
                if isinstance(data, BaseModel):
                    data = data.model_dump()
                    
                part = Part(root=DataPart(data=data))
            else:
                # Convert to string if needed
                text = str(data)
                part = Part(root=TextPart(text=text))
            
            await updater.add_artifact(
                parts=[part],
                name=name,
                artifact_id=artifact_id
            )
            
        except Exception as e:
            logger.error(f"Failed to add artifact {artifact_id}: {e}")
            # Don't raise - artifacts are supplementary
    
    @staticmethod
    async def send_error(
        updater: TaskUpdater,
        error: Exception,
        context: Optional[str] = None
    ) -> None:
        """
        Send error message via updater.
        
        Args:
            updater: Task updater for sending error
            error: The exception that occurred
            context: Optional context about where error occurred
        """
        error_message = str(error)
        
        if context:
            error_message = f"{context}: {error_message}"
        
        await updater.failed(
            message=updater.new_agent_message(
                [Part(root=TextPart(text=f"Error: {error_message}"))]
            )
        )
    
    @staticmethod
    def create_summary(
        agent_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a standardized summary message.
        
        Args:
            agent_name: Name of the agent
            action: What action was performed
            details: Optional details to include
            
        Returns:
            Formatted summary string
        """
        summary = f"{agent_name} {action}"
        
        if details:
            detail_parts = []
            for key, value in details.items():
                if value is not None:
                    detail_parts.append(f"{key}: {value}")
            
            if detail_parts:
                summary += f" ({', '.join(detail_parts)})"
        
        return summary