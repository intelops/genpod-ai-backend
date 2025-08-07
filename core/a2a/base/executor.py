"""
Base A2A Executor implementing Template Method pattern.

This abstract class defines the algorithm for handling A2A requests,
while allowing subclasses to override specific steps.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional, TypeVar, Generic
from pydantic import BaseModel

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Message, Task, TaskState, TaskStatus, Part, TextPart
from datetime import datetime, timezone
import uuid

from core.agent import BaseAgent
from core.a2a.exceptions import (
    A2AExecutionError,
    A2AInputExtractionError,
)
from utils.logger import logger

# Type variables for input/output models
TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)
TAgent = TypeVar('TAgent', bound=BaseAgent)


class BaseA2AExecutor(AgentExecutor, ABC, Generic[TAgent, TInput, TOutput]):
    """
    Base executor for A2A protocol implementation.
    
    This class implements the Template Method pattern, defining the overall
    algorithm for handling A2A requests while allowing subclasses to customize
    specific steps.
    
    Type Parameters:
        TAgent: The type of agent this executor wraps
        TInput: The Pydantic model for agent input
        TOutput: The Pydantic model for agent output
    """
    
    def __init__(self, agent: TAgent, agent_name: str):
        """
        Initialize the base executor.
        
        Args:
            agent: The GenPod agent instance to wrap
            agent_name: Name of the agent for logging
        """
        self.agent = agent
        self.agent_name = agent_name
        self.active_tasks: Dict[str, asyncio.Task] = {}
        logger.info(f"Initialized {agent_name} A2A Executor")
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute the agent for a given request (Template Method).
        
        This method defines the overall algorithm:
        1. Get or create task
        2. Extract input from message
        3. Execute agent
        4. Handle response
        
        Args:
            context: Request context containing message and metadata
            event_queue: Queue for publishing events
        """
        task = await self._ensure_task(context, event_queue)
        task_id = task.id
        context_id = task.context_id
        
        logger.info(f"[A2A-{self.agent_name}] Executing task {task_id}")
        
        # Create TaskUpdater for state management
        updater = TaskUpdater(event_queue, task_id, context_id)
        
        try:
            # Start work
            await updater.start_work()
            
            # Extract input (delegated to subclass)
            agent_input = await self._extract_input(context.message)
            
            # Create async task for cancellation support
            async_task = asyncio.create_task(
                self._run_agent_task(agent_input, task_id, context_id, updater)
            )
            self.active_tasks[task_id] = async_task
            
            # Wait for completion
            await async_task
            
        except asyncio.CancelledError:
            logger.info(f"[A2A-{self.agent_name}] Task {task_id} cancelled")
            await updater.cancel()
        except Exception as e:
            logger.error(f"[A2A-{self.agent_name}] Task {task_id} failed: {str(e)}")
            await self._handle_error(e, updater)
        finally:
            self.active_tasks.pop(task_id, None)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Cancel an ongoing task.
        
        Args:
            context: Request context containing task ID
            event_queue: Queue for publishing cancellation event
        """
        task_id = context.task_id
        if task_id in self.active_tasks:
            logger.info(f"[A2A-{self.agent_name}] Cancelling task {task_id}")
            self.active_tasks[task_id].cancel()
        else:
            logger.warning(f"[A2A-{self.agent_name}] Task {task_id} not found for cancellation")
            updater = TaskUpdater(event_queue, task_id, context.context_id or "")
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=TextPart(text="Task not found"))]
                )
            )
    
    async def _ensure_task(self, context: RequestContext, event_queue: EventQueue) -> Task:
        """
        Ensure a task exists for the request.
        
        Args:
            context: Request context
            event_queue: Event queue for publishing new task
            
        Returns:
            Task instance
        """
        if context.current_task:
            return context.current_task
            
        # Create new task
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            context_id=context_id,
            status=TaskStatus(
                state=TaskState.submitted,
                timestamp=datetime.now(timezone.utc).isoformat()
            ),
            history=[context.message] if context.message else []
        )
        
        await event_queue.enqueue_event(task)
        return task
    
    async def _run_agent_task(
        self,
        agent_input: TInput,
        task_id: str,
        _: str,  # context_id not used but kept for compatibility
        updater: TaskUpdater
    ) -> None:
        """
        Run the agent and manage response.
        
        Args:
            agent_input: Validated input for the agent
            task_id: Current task ID
            context_id: Current context ID
            updater: Task updater for state management
        """
        try:
            # Execute agent (delegated to subclass)
            agent_output = await self._execute_agent(agent_input, task_id)
            
            # Format response (delegated to subclass)
            await self._format_response(agent_output, updater)
            
            # Mark as completed
            await updater.complete()
            logger.info(f"[A2A-{self.agent_name}] Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"[A2A-{self.agent_name}] Error in task {task_id}: {str(e)}")
            raise
    
    async def _handle_error(self, error: Exception, updater: TaskUpdater) -> None:
        """
        Handle errors during execution.
        
        Args:
            error: The exception that occurred
            updater: Task updater for sending error message
        """
        error_message = f"Error: {str(error)}"
        
        if isinstance(error, A2AInputExtractionError):
            error_message = f"Invalid input: {str(error)}"
        elif isinstance(error, A2AExecutionError):
            error_message = f"Execution failed: {str(error)}"
            
        await updater.failed(
            message=updater.new_agent_message(
                [Part(root=TextPart(text=error_message))]
            )
        )
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def _extract_input(self, message: Optional[Message]) -> TInput:
        """
        Extract and validate input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated input model
            
        Raises:
            A2AInputExtractionError: If extraction fails
        """
        pass
    
    @abstractmethod
    async def _execute_agent(self, agent_input: TInput, task_id: str) -> TOutput:
        """
        Execute the agent with the given input.
        
        Args:
            agent_input: Validated input for the agent
            task_id: Current task ID
            
        Returns:
            Agent output
            
        Raises:
            A2AExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    async def _format_response(self, agent_output: TOutput, updater: TaskUpdater) -> None:
        """
        Format agent output and send via updater.
        
        Args:
            agent_output: Output from the agent
            updater: Task updater for sending response
        """
        pass