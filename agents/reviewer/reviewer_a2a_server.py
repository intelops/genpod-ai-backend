"""
A2A Protocol Server for Reviewer Agent

This module wraps the Reviewer agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.reviewer.reviewer_agent import ReviewerAgent
from agents.reviewer._internal.reviewer_state import ReviewerState, ReviewerInput, ReviewerOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class ReviewerA2AExecutor(BaseA2AExecutor[ReviewerAgent, ReviewerInput, ReviewerOutput]):
    """
    A2A Protocol executor for the Reviewer agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    reviewer-specific input/output processing.
    """
    
    def __init__(self, reviewer_agent: ReviewerAgent):
        """
        Initialize the Reviewer A2A executor.
        
        Args:
            reviewer_agent: The underlying GenPod Reviewer agent instance
        """
        super().__init__(reviewer_agent, "Reviewer")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> ReviewerInput:
        """
        Extract and validate reviewer input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated ReviewerInput instance
        """
        try:
            # Extract input using the common extractor
            reviewer_input = self.extractor.extract_agent_input(
                message=message,
                input_model=ReviewerInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not reviewer_input.project_name:
                raise ValueError("project_name is required")
            
            if not reviewer_input.requirements_document:
                raise ValueError("requirements_document is required")
                
            logger.debug(f"[A2A-Reviewer] Extracted input for project: {reviewer_input.project_name}")
            return reviewer_input
            
        except Exception as e:
            logger.error(f"[A2A-Reviewer] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: ReviewerInput, task_id: str) -> ReviewerOutput:
        """
        Execute the reviewer agent with given input.
        
        Args:
            agent_input: Validated input for the reviewer
            task_id: Current task ID
            
        Returns:
            ReviewerOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = ReviewerState(**agent_input.model_dump())
            
            # Run the reviewer agent graph
            logger.info(f"[A2A-Reviewer] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Reviewer] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return ReviewerOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Reviewer] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Reviewer execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: ReviewerOutput, updater: TaskUpdater) -> None:
        """
        Format reviewer output and send response.
        
        Args:
            agent_output: Output from the reviewer agent
            updater: Task updater for sending response
        """
        # Create summary
        issue_count = len(agent_output.issues.items) if agent_output.issues else 0
        summary = self.formatter.create_summary(
            agent_name="Reviewer",
            action="completed code review",
            details={
                "issues_found": issue_count,
                "status": "passed" if issue_count == 0 else "needs_fixes"
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
        if agent_output.issues and agent_output.issues.items:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.issues,
                name="Review Issues",
                artifact_id="review-issues"
            )


class ReviewerAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Reviewer agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define reviewer-specific skills."""
        return [
            AgentSkill(
                id="code-review",
                name="Code Review",
                description="Reviews code for quality, security, and best practices",
                tags=["review", "quality", "security", "best-practices"],
                examples=[
                    "Review code for security vulnerabilities",
                    "Check code quality and adherence to standards",
                    "Identify performance issues and optimizations"
                ]
            ),
            AgentSkill(
                id="documentation-review",
                name="Documentation Review",
                description="Reviews and generates project documentation",
                tags=["documentation", "review", "generation"],
                examples=[
                    "Review API documentation completeness",
                    "Generate missing documentation",
                    "Ensure documentation matches implementation"
                ]
            )
        ]


def create_reviewer_a2a_app(
    reviewer_agent: ReviewerAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Reviewer agent.
    
    Args:
        reviewer_agent: The GenPod Reviewer agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("reviewer")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Reviewer agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = ReviewerA2AExecutor(reviewer_agent)
    
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
        ReviewerAgentCardBuilder("Reviewer", "1.0.0")
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
        title="GenPod Reviewer Agent (A2A)",
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
            "agent": "reviewer",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app