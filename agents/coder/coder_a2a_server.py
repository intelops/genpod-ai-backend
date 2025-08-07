"""
A2A Protocol Server for Coder Agent

This module wraps the Coder agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.coder.coder_agent import CoderAgent
from agents.coder._internal.coder_state import CoderState, CoderInput, CoderOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class CoderA2AExecutor(BaseA2AExecutor[CoderAgent, CoderInput, CoderOutput]):
    """
    A2A Protocol executor for the Coder agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    coder-specific input/output processing.
    """
    
    def __init__(self, coder_agent: CoderAgent):
        """
        Initialize the Coder A2A executor.
        
        Args:
            coder_agent: The underlying GenPod Coder agent instance
        """
        super().__init__(coder_agent, "Coder")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> CoderInput:
        """
        Extract and validate coder input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated CoderInput instance
        """
        try:
            # Extract input using the common extractor
            coder_input = self.extractor.extract_agent_input(
                message=message,
                input_model=CoderInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not coder_input.project_name:
                raise ValueError("project_name is required")
            
            if not coder_input.requirements_document:
                raise ValueError("requirements_document is required")
                
            logger.debug(f"[A2A-Coder] Extracted input for project: {coder_input.project_name}")
            return coder_input
            
        except Exception as e:
            logger.error(f"[A2A-Coder] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: CoderInput, task_id: str) -> CoderOutput:
        """
        Execute the coder agent with given input.
        
        Args:
            agent_input: Validated input for the coder
            task_id: Current task ID
            
        Returns:
            CoderOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = CoderState(**agent_input.model_dump())
            
            # Run the coder agent graph
            logger.info(f"[A2A-Coder] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Coder] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return CoderOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Coder] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Coder execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: CoderOutput, updater: TaskUpdater) -> None:
        """
        Format coder output and send response.
        
        Args:
            agent_output: Output from the coder agent
            updater: Task updater for sending response
        """
        # Create summary
        code_plans = len(agent_output.code_generation_plan_list) if agent_output.code_generation_plan_list else 0
        summary = self.formatter.create_summary(
            agent_name="Coder",
            action="completed code implementation",
            details={
                "task": agent_output.current_planned_task.task_id if agent_output.current_planned_task else "N/A",
                "code_plans": code_plans
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
        if agent_output.code_generation_plan_list:
            await self.formatter.add_artifact(
                updater=updater,
                data={"plans": [plan.model_dump() for plan in agent_output.code_generation_plan_list]},
                name="Code Generation Plans",
                artifact_id="code-generation-plans"
            )


class CoderAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Coder agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define coder-specific skills."""
        return [
            AgentSkill(
                id="code-implementation",
                name="Code Implementation",
                description="Implements code based on specifications and requirements",
                tags=["coding", "implementation", "development"],
                examples=[
                    "Implement the user authentication module",
                    "Create database models for the inventory system",
                    "Write API endpoints for CRUD operations"
                ]
            ),
            AgentSkill(
                id="code-generation",
                name="Code Generation",
                description="Generates boilerplate code and project structure",
                tags=["generation", "scaffolding", "templates"],
                examples=[
                    "Generate project structure for a microservice",
                    "Create boilerplate for REST API",
                    "Generate test templates"
                ]
            )
        ]


def create_coder_a2a_app(
    coder_agent: CoderAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Coder agent.
    
    Args:
        coder_agent: The GenPod Coder agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("coder")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Coder agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = CoderA2AExecutor(coder_agent)
    
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
        CoderAgentCardBuilder("Coder", "1.0.0")
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
        title="GenPod Coder Agent (A2A)",
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
            "agent": "coder",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app