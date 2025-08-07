"""
A2A Protocol Server for Research Agent

This module wraps the Research agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.research.research_agent import ResearchAgent
from agents.research._internal.research_state import ResearchState, ResearchInput, ResearchOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class ResearchA2AExecutor(BaseA2AExecutor[ResearchAgent, ResearchInput, ResearchOutput]):
    """
    A2A Protocol executor for the Research agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    research-specific input/output processing.
    """
    
    def __init__(self, research_agent: ResearchAgent):
        """
        Initialize the Research A2A executor.
        
        Args:
            research_agent: The underlying GenPod Research agent instance
        """
        super().__init__(research_agent, "Research")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> ResearchInput:
        """
        Extract and validate research input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated ResearchInput instance
        """
        try:
            # Extract input using the common extractor
            research_input = self.extractor.extract_agent_input(
                message=message,
                input_model=ResearchInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not research_input.query:
                raise ValueError("query is required")
                
            logger.debug(f"[A2A-Research] Extracted query: {research_input.query[:50]}...")
            return research_input
            
        except Exception as e:
            logger.error(f"[A2A-Research] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: ResearchInput, task_id: str) -> ResearchOutput:
        """
        Execute the research agent with given input.
        
        Args:
            agent_input: Validated input for the research agent
            task_id: Current task ID
            
        Returns:
            ResearchOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = ResearchState(**agent_input.model_dump())
            
            # Run the research agent graph
            logger.info(f"[A2A-Research] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-Research] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return ResearchOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-Research] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Research execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: ResearchOutput, updater: TaskUpdater) -> None:
        """
        Format research output and send response.
        
        Args:
            agent_output: Output from the research agent
            updater: Task updater for sending response
        """
        # Create summary
        summary = self.formatter.create_summary(
            agent_name="Research",
            action="completed research",
            details={
                "response_type": str(agent_output.response_type),
                "response_length": len(agent_output.response) if agent_output.response else 0,
                "metadata_keys": list(agent_output.metadata.keys()) if agent_output.metadata else []
            }
        )
        
        # Send main response
        await self.formatter.send_agent_output(
            updater=updater,
            output_model=agent_output,
            summary=summary,
            field_name="agent_output"
        )
        
        # Add artifacts if metadata exists
        if agent_output.metadata:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.metadata,
                name="Research Metadata",
                artifact_id="research-metadata"
            )


class ResearchAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Research agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define research-specific skills."""
        return [
            AgentSkill(
                id="information-retrieval",
                name="Information Retrieval",
                description="Retrieves and analyzes information from various sources",
                tags=["research", "retrieval", "analysis", "information"],
                examples=[
                    "Research best practices for microservices",
                    "Find information about specific technologies",
                    "Gather documentation on APIs and frameworks"
                ]
            ),
            AgentSkill(
                id="web-search",
                name="Web Search Integration",
                description="Performs web searches to gather current information",
                tags=["search", "web", "internet", "current-events"],
                examples=[
                    "Search for latest updates on a technology",
                    "Find recent security vulnerabilities",
                    "Research current industry trends"
                ]
            )
        ]


def create_research_a2a_app(
    research_agent: ResearchAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Research agent.
    
    Args:
        research_agent: The GenPod Research agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("research")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Research agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = ResearchA2AExecutor(research_agent)
    
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
        ResearchAgentCardBuilder("Research", "1.0.0")
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
        title="GenPod Research Agent (A2A)",
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
            "agent": "research",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app