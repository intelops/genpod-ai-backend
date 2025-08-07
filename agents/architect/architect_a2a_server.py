"""
A2A Protocol Server for Architect Agent

This module wraps the Architect agent to expose it via the A2A (Agent-to-Agent) protocol.
Follows SOLID principles and uses the base infrastructure for consistency.
"""

import asyncio
from typing import List, Optional

from fastapi import FastAPI
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.database_task_store import DatabaseTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentSkill, Message
from sqlalchemy.ext.asyncio import create_async_engine

from agents.architect.architect_agent import ArchitectAgent
from agents.architect._internal.architect_state import ArchitectState, ArchitectInput, ArchitectOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class ArchitectA2AExecutor(BaseA2AExecutor[ArchitectAgent, ArchitectInput, ArchitectOutput]):
    """
    A2A Protocol executor for the Architect agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    architect-specific input/output processing.
    """
    
    def __init__(self, architect_agent: ArchitectAgent):
        """
        Initialize the Architect A2A executor.
        
        Args:
            architect_agent: The underlying GenPod Architect agent instance
        """
        super().__init__(architect_agent, "Architect")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> ArchitectInput:
        """
        Extract and validate architect input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated ArchitectInput instance
        """
        try:
            # Extract input using the common extractor
            architect_input = self.extractor.extract_agent_input(
                message=message,
                input_model=ArchitectInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not architect_input.user_prompt:
                raise ValueError("user_prompt is required")
            
            if not architect_input.project_directory:
                raise ValueError("project_directory is required")
                
            logger.debug(f"[A2A-Architect] Extracted input for project: {architect_input.project_directory}")
            return architect_input
            
        except Exception as e:
            logger.error(f"[A2A-Architect] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: ArchitectInput, task_id: str) -> ArchitectOutput:
        """
        Execute the architect agent with given input.
        
        Args:
            agent_input: Validated input for the architect
            task_id: Current task ID
            
        Returns:
            ArchitectOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = ArchitectState(**agent_input.model_dump())
            
            # Run the architect agent graph
            logger.info(f"[A2A-Architect] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Architect] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return ArchitectOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Architect] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Architect execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: ArchitectOutput, updater: TaskUpdater) -> None:
        """
        Format architect output and send response.
        
        Args:
            agent_output: Output from the architect agent
            updater: Task updater for sending response
        """
        # Create summary
        task_count = len(agent_output.tasks.items) if agent_output.tasks else 0
        summary = self.formatter.create_summary(
            agent_name="Architect",
            action="completed architecture design",
            details={
                "project": agent_output.project_name,
                "tasks": task_count
            }
        )
        
        # Send main response
        await self.formatter.send_agent_output(
            updater=updater,
            output_model=agent_output,
            summary=summary,
            field_name="agent_output"
        )
        
        # Add artifacts
        if agent_output.requirements_document:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.requirements_document,
                name="Requirements Document",
                artifact_id="requirements-document"
            )
        
        if agent_output.tasks:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.tasks,
                name="Project Tasks",
                artifact_id="task-queue"
            )
    


class ArchitectAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Architect agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define architect-specific skills."""
        return [
            AgentSkill(
                id="project-architecture",
                name="Project Architecture Design",
                description="Creates detailed project architecture with requirements and task breakdown",
                tags=["architecture", "design", "requirements", "planning"],
                examples=[
                    "Design a REST API for user management",
                    "Create architecture for a microservices-based e-commerce platform",
                    "Plan a data pipeline for real-time analytics"
                ]
            )
        ]


def create_architect_a2a_app(
    architect_agent: ArchitectAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Architect agent.
    
    Args:
        architect_agent: The GenPod Architect agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("architect")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Architect agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = ArchitectA2AExecutor(architect_agent)
    
    # Create request handler
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        queue_manager=None,  # Will use default InMemoryQueueManager
        push_config_store=None,
        push_sender=None,
        request_context_builder=None
    )
    
    # Create agent card using builder
    agent_card = (
        ArchitectAgentCardBuilder("Architect", "1.0.0")
        .with_description(agent_config.description)
        .with_url(f"http://{agent_config.host}:{agent_config.port}")
        .with_capabilities(streaming=True, push_notifications=False)
        .build()
    )
    
    # Create A2A application
    a2a_app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=handler
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="GenPod Architect Agent (A2A)",
        description=agent_config.description,
        version="1.0.0"
    )
    
    # Add A2A routes
    a2a_app.add_routes_to_app(app)
    
    # Add health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "agent": "architect",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app
