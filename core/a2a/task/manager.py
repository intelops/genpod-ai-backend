"""
Task lifecycle management for A2A protocol.

Implements Facade pattern to simplify task operations.
"""

from typing import Optional
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.server.events.event_queue import EventQueue
from a2a.types import Task, TaskState
from core.a2a.exceptions import A2ATaskManagementError
from utils.logger import logger


class TaskManager:
    """
    Manages task lifecycle operations.
    
    This class acts as a Facade, providing a simplified interface
    for common task management operations.
    """
    
    def __init__(self, event_queue: EventQueue):
        """
        Initialize task manager.
        
        Args:
            event_queue: Event queue for task updates
        """
        self.event_queue = event_queue
    
    def create_updater(self, task_id: str, context_id: str) -> TaskUpdater:
        """
        Create a new task updater.
        
        Args:
            task_id: ID of the task
            context_id: Context ID for the task
            
        Returns:
            TaskUpdater instance
        """
        return TaskUpdater(self.event_queue, task_id, context_id)
    
    async def start_task(self, updater: TaskUpdater) -> None:
        """
        Mark task as started.
        
        Args:
            updater: Task updater instance
        """
        try:
            await updater.start_work()
            logger.debug(f"Task {updater.task_id} marked as working")
        except Exception as e:
            raise A2ATaskManagementError(f"Failed to start task: {str(e)}")
    
    async def complete_task(self, updater: TaskUpdater) -> None:
        """
        Mark task as completed.
        
        Args:
            updater: Task updater instance
        """
        try:
            await updater.complete()
            logger.debug(f"Task {updater.task_id} marked as completed")
        except Exception as e:
            raise A2ATaskManagementError(f"Failed to complete task: {str(e)}")
    
    async def fail_task(
        self,
        updater: TaskUpdater,
        error_message: str
    ) -> None:
        """
        Mark task as failed with error message.
        
        Args:
            updater: Task updater instance
            error_message: Error message to include
        """
        try:
            from a2a.types import Part, TextPart
            
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=TextPart(text=error_message))]
                )
            )
            logger.debug(f"Task {updater.task_id} marked as failed: {error_message}")
        except Exception as e:
            raise A2ATaskManagementError(f"Failed to mark task as failed: {str(e)}")
    
    async def cancel_task(self, updater: TaskUpdater) -> None:
        """
        Mark task as cancelled.
        
        Args:
            updater: Task updater instance
        """
        try:
            await updater.cancel()
            logger.debug(f"Task {updater.task_id} marked as cancelled")
        except Exception as e:
            raise A2ATaskManagementError(f"Failed to cancel task: {str(e)}")
    
    @staticmethod
    def get_task_state(task: Task) -> TaskState:
        """
        Get current state of a task.
        
        Args:
            task: Task instance
            
        Returns:
            Current task state
        """
        return task.status.state
    
    @staticmethod
    def is_terminal_state(state: TaskState) -> bool:
        """
        Check if task state is terminal (no further updates expected).
        
        Args:
            state: Task state to check
            
        Returns:
            True if state is terminal
        """
        terminal_states = {
            TaskState.completed,
            TaskState.failed,
            TaskState.canceled,
            TaskState.rejected,
            TaskState.unknown
        }
        return state in terminal_states