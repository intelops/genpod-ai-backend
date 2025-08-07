"""
A2A Protocol Server for RAG Middleware Agent

This module wraps the RAG Middleware agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.rag_middleware.rag_middleware import RAGMiddleware
from agents.rag_middleware._internal.rag_middleware_state import (
    RAGMiddlewareState, RAGMiddlewareInput, RAGMiddlewareOutput
)
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class RAGMiddlewareA2AExecutor(BaseA2AExecutor[RAGMiddleware, RAGMiddlewareInput, RAGMiddlewareOutput]):
    """
    A2A Protocol executor for the RAG Middleware agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    RAG middleware-specific input/output processing.
    """
    
    def __init__(self, rag_middleware: RAGMiddleware):
        """
        Initialize the RAG Middleware A2A executor.
        
        Args:
            rag_middleware: The underlying GenPod RAG Middleware instance
        """
        super().__init__(rag_middleware, "RAGMiddleware")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> RAGMiddlewareInput:
        """
        Extract and validate RAG middleware input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated RAGMiddlewareInput instance
        """
        try:
            # Extract input using the common extractor
            middleware_input = self.extractor.extract_agent_input(
                message=message,
                input_model=RAGMiddlewareInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not middleware_input.query:
                raise ValueError("query is required")
            if not middleware_input.agent_id:
                raise ValueError("agent_id is required")
            if not middleware_input.task_id:
                raise ValueError("task_id is required")
                
            logger.debug(f"[A2A-RAGMiddleware] Extracted query: {middleware_input.query[:50]}... from agent: {middleware_input.agent_id}")
            return middleware_input
            
        except Exception as e:
            logger.error(f"[A2A-RAGMiddleware] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: RAGMiddlewareInput, task_id: str) -> RAGMiddlewareOutput:
        """
        Execute the RAG middleware with given input.
        
        Args:
            agent_input: Validated input for the RAG middleware
            task_id: Current task ID
            
        Returns:
            RAGMiddlewareOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = RAGMiddlewareState(**agent_input.model_dump())
            
            # Run the RAG middleware graph
            logger.info(f"[A2A-RAGMiddleware] Executing middleware workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-RAGMiddleware] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return RAGMiddlewareOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-RAGMiddleware] Failed to execute middleware: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"RAG Middleware execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: RAGMiddlewareOutput, updater: TaskUpdater) -> None:
        """
        Format RAG middleware output and send response.
        
        Args:
            agent_output: Output from the RAG middleware
            updater: Task updater for sending response
        """
        # Create summary
        summary = self.formatter.create_summary(
            agent_name="RAGMiddleware",
            action="completed RAG agent selection and query processing",
            details={
                "response_type": agent_output.response_type.value if hasattr(agent_output.response_type, 'value') else str(agent_output.response_type),
                "selected_agent": agent_output.selected_rag_agent.get("name", "None") if agent_output.selected_rag_agent else "None",
                "selection_count": len(agent_output.selection_details) if agent_output.selection_details else 0
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
        if agent_output.selection_details:
            await self.formatter.add_artifact(
                updater=updater,
                data={"selection_details": agent_output.selection_details},
                name="RAG Agent Selection Details",
                artifact_id="selection-details"
            )


class RAGMiddlewareAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for RAG Middleware agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define RAG middleware-specific skills."""
        return [
            AgentSkill(
                id="rag-agent-selection",
                name="RAG Agent Selection",
                description="Intelligently selects the most appropriate RAG agent for a given query",
                tags=["rag", "middleware", "selection", "routing", "orchestration"],
                examples=[
                    "Route queries to specialized RAG agents",
                    "Select agents based on query context and confidence scores",
                    "Handle fallback scenarios when no suitable agent is found"
                ]
            ),
            AgentSkill(
                id="query-caching",
                name="Query Response Caching",
                description="Caches query-response pairs for efficient retrieval",
                tags=["cache", "optimization", "performance", "fuzzy-matching"],
                examples=[
                    "Cache frequently asked questions",
                    "Perform fuzzy matching on similar queries",
                    "Reduce redundant RAG agent invocations"
                ]
            ),
            AgentSkill(
                id="error-tracking",
                name="Error and Task Tracking",
                description="Tracks errors and maintains agent task history",
                tags=["monitoring", "error-handling", "tracking", "reliability"],
                examples=[
                    "Track error counts per agent and task",
                    "Maintain agent task history",
                    "Handle agent failures gracefully"
                ]
            )
        ]


def create_rag_middleware_a2a_app(
    rag_middleware: RAGMiddleware,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the RAG Middleware agent.
    
    Args:
        rag_middleware: The GenPod RAG Middleware instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("rag_middleware")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("RAG Middleware agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = RAGMiddlewareA2AExecutor(rag_middleware)
    
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
        RAGMiddlewareAgentCardBuilder("RAGMiddleware", "1.0.0")
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
        title="GenPod RAG Middleware Agent (A2A)",
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
            "agent": "rag_middleware",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app