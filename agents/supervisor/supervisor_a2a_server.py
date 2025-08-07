"""
A2A Protocol Server for Supervisor Agent

This module wraps the Supervisor agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor._internal.supervisor_state import SupervisorState, SupervisorInput, SupervisorOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class SupervisorA2AExecutor(BaseA2AExecutor[SupervisorAgent, SupervisorInput, SupervisorOutput]):
    """
    A2A Protocol executor for the Supervisor agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    supervisor-specific input/output processing.
    """
    
    def __init__(self, supervisor_agent: SupervisorAgent):
        """
        Initialize the Supervisor A2A executor.
        
        Args:
            supervisor_agent: The underlying GenPod Supervisor agent instance
        """
        super().__init__(supervisor_agent, "Supervisor")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> SupervisorInput:
        """
        Extract and validate supervisor input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated SupervisorInput instance
        """
        try:
            # Extract input using the common extractor
            supervisor_input = self.extractor.extract_agent_input(
                message=message,
                input_model=SupervisorInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not supervisor_input.user_prompt:
                raise ValueError("user_prompt is required")
            
            if not supervisor_input.project_directory:
                raise ValueError("project_directory is required")
            
            if not supervisor_input.project_id:
                raise ValueError("project_id is required")
                
            logger.debug(f"[A2A-Supervisor] Extracted input for project: {supervisor_input.project_directory}")
            return supervisor_input
            
        except Exception as e:
            logger.error(f"[A2A-Supervisor] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: SupervisorInput, task_id: str) -> SupervisorOutput:
        """
        Execute the supervisor agent with given input.
        
        Args:
            agent_input: Validated input for the supervisor
            task_id: Current task ID
            
        Returns:
            SupervisorOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = SupervisorState(**agent_input.model_dump())
            
            # Run the supervisor agent graph
            logger.info(f"[A2A-Supervisor] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Supervisor] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return SupervisorOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Supervisor] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Supervisor execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: SupervisorOutput, updater: TaskUpdater) -> None:
        """
        Format supervisor output and send response.
        
        Args:
            agent_output: Output from the supervisor agent
            updater: Task updater for sending response
        """
        # Create summary
        task_count = len(agent_output.tasks.items) if agent_output.tasks else 0
        issue_count = len(agent_output.issues.items) if agent_output.issues else 0
        
        summary = self.formatter.create_summary(
            agent_name="Supervisor",
            action="completed orchestration",
            details={
                "application": agent_output.application_name,
                "project_status": agent_output.project_status.value if agent_output.project_status else "unknown",
                "tasks": task_count,
                "issues": issue_count
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
        if agent_output.tasks and agent_output.tasks.items:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.tasks,
                name="Generated Tasks",
                artifact_id="generated-tasks"
            )
        
        if agent_output.issues and agent_output.issues.items:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.issues,
                name="Identified Issues",
                artifact_id="identified-issues"
            )


class SupervisorAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Supervisor agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define supervisor-specific skills."""
        return [
            AgentSkill(
                id="agent-orchestration",
                name="Agent Orchestration",
                description="Orchestrates multiple agents to complete complex tasks",
                tags=["orchestration", "coordination", "workflow", "management"],
                examples=[
                    "Coordinate architect, coder, and reviewer agents",
                    "Manage complex multi-agent workflows",
                    "Handle task distribution and result aggregation"
                ]
            ),
            AgentSkill(
                id="project-management",
                name="Project Management",
                description="Manages project lifecycle and tracks progress",
                tags=["project", "management", "tracking", "status"],
                examples=[
                    "Track project development status",
                    "Manage task queues and issue resolution",
                    "Monitor agent performance and completion"
                ]
            )
        ]


def create_supervisor_a2a_app(
    supervisor_agent: SupervisorAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Supervisor agent.
    
    Args:
        supervisor_agent: The GenPod Supervisor agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("supervisor")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Supervisor agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = SupervisorA2AExecutor(supervisor_agent)
    
    # Create request handler
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        queue_manager=None,
        push_config_store=None,
        push_sender=None,
        request_context_builder=None
    )
    
    # Create agent card using builder
    agent_card = (
        SupervisorAgentCardBuilder("Supervisor", "1.0.0")
        .with_description(agent_config.description)
        .with_url(f"http://{agent_config.host}:{agent_config.port}/")
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
        title="GenPod Supervisor Agent (A2A)",
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
            "agent": "supervisor",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app