"""
A2A Protocol Server for Planner Agent

This module wraps the Planner agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.planner.planner_agent import PlannerAgent
from agents.planner._internal.planner_state import PlannerState, PlannerInput, PlannerOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class PlannerA2AExecutor(BaseA2AExecutor[PlannerAgent, PlannerInput, PlannerOutput]):
    """
    A2A Protocol executor for the Planner agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    planner-specific input/output processing.
    """
    
    def __init__(self, planner_agent: PlannerAgent):
        """
        Initialize the Planner A2A executor.
        
        Args:
            planner_agent: The underlying GenPod Planner agent instance
        """
        super().__init__(planner_agent, "Planner")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> PlannerInput:
        """
        Extract and validate planner input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated PlannerInput instance
        """
        try:
            # Extract input using the common extractor
            planner_input = self.extractor.extract_agent_input(
                message=message,
                input_model=PlannerInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not planner_input.requirements_document:
                raise ValueError("requirements_document is required")
                
            logger.debug(f"[A2A-Planner] Extracted input with {len(planner_input.deliverable_list.items)} deliverables")
            return planner_input
            
        except Exception as e:
            logger.error(f"[A2A-Planner] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: PlannerInput, task_id: str) -> PlannerOutput:
        """
        Execute the planner agent with given input.
        
        Args:
            agent_input: Validated input for the planner
            task_id: Current task ID
            
        Returns:
            PlannerOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = PlannerState(**agent_input.model_dump())
            
            # Run the planner agent graph
            logger.info(f"[A2A-Planner] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Planner] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return PlannerOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Planner] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Planner execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: PlannerOutput, updater: TaskUpdater) -> None:
        """
        Format planner output and send response.
        
        Args:
            agent_output: Output from the planner agent
            updater: Task updater for sending response
        """
        # Create summary
        task_count = len(agent_output.planned_tasks.items) if agent_output.planned_tasks else 0
        issue_count = len(agent_output.planned_issues.items) if agent_output.planned_issues else 0
        
        summary = self.formatter.create_summary(
            agent_name="Planner",
            action="completed planning",
            details={
                "planned_tasks": task_count,
                "planned_issues": issue_count
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
        if agent_output.planned_tasks and agent_output.planned_tasks.items:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.planned_tasks,
                name="Planned Tasks",
                artifact_id="planned-tasks"
            )
        
        if agent_output.planned_issues and agent_output.planned_issues.items:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.planned_issues,
                name="Planned Issues",
                artifact_id="planned-issues"
            )


class PlannerAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Planner agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define planner-specific skills."""
        return [
            AgentSkill(
                id="task-planning",
                name="Task Planning",
                description="Creates detailed task breakdowns and work packages",
                tags=["planning", "tasks", "breakdown", "organization"],
                examples=[
                    "Break down a feature into implementable tasks",
                    "Create work packages for issue resolution",
                    "Plan sprint tasks based on requirements"
                ]
            ),
            AgentSkill(
                id="issue-planning",
                name="Issue Planning",
                description="Analyzes and plans resolution for identified issues",
                tags=["issues", "analysis", "resolution", "planning"],
                examples=[
                    "Plan fixes for code review issues",
                    "Create action items for bug fixes",
                    "Prioritize and organize issue resolution"
                ]
            )
        ]


def create_planner_a2a_app(
    planner_agent: PlannerAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Planner agent.
    
    Args:
        planner_agent: The GenPod Planner agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("planner")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Planner agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = PlannerA2AExecutor(planner_agent)
    
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
        PlannerAgentCardBuilder("Planner", "1.0.0")
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
        title="GenPod Planner Agent (A2A)",
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
            "agent": "planner",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app