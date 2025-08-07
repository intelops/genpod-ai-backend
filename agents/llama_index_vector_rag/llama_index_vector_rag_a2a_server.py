"""
A2A Protocol Server for LlamaIndex Vector RAG Agent

This module wraps the LlamaIndex Vector RAG agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.llama_index_vector_rag.llama_index_vector_rag import LlamaIndexVectorRAGAgent
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_state import (
    LlamaIndexVectorState, LlamaIndexVectorInput, LlamaIndexVectorOutput
)
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class LlamaIndexVectorRAGA2AExecutor(BaseA2AExecutor[LlamaIndexVectorRAGAgent, LlamaIndexVectorInput, LlamaIndexVectorOutput]):
    """
    A2A Protocol executor for the LlamaIndex Vector RAG agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    RAG-specific input/output processing.
    """
    
    def __init__(self, rag_agent: LlamaIndexVectorRAGAgent):
        """
        Initialize the LlamaIndex Vector RAG A2A executor.
        
        Args:
            rag_agent: The underlying GenPod RAG agent instance
        """
        super().__init__(rag_agent, "LlamaIndexVectorRAG")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> LlamaIndexVectorInput:
        """
        Extract and validate RAG input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated LlamaIndexVectorInput instance
        """
        try:
            # Extract input using the common extractor
            rag_input = self.extractor.extract_agent_input(
                message=message,
                input_model=LlamaIndexVectorInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not rag_input.query:
                raise ValueError("query is required")
                
            logger.debug(f"[A2A-LlamaIndexVectorRAG] Extracted query: {rag_input.query[:50]}...")
            return rag_input
            
        except Exception as e:
            logger.error(f"[A2A-LlamaIndexVectorRAG] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: LlamaIndexVectorInput, task_id: str) -> LlamaIndexVectorOutput:
        """
        Execute the RAG agent with given input.
        
        Args:
            agent_input: Validated input for the RAG agent
            task_id: Current task ID
            
        Returns:
            LlamaIndexVectorOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = LlamaIndexVectorState(**agent_input.model_dump())
            
            # Run the RAG agent graph
            logger.info(f"[A2A-LlamaIndexVectorRAG] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-LlamaIndexVectorRAG] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return LlamaIndexVectorOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-LlamaIndexVectorRAG] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"LlamaIndex Vector RAG execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: LlamaIndexVectorOutput, updater: TaskUpdater) -> None:
        """
        Format RAG output and send response.
        
        Args:
            agent_output: Output from the RAG agent
            updater: Task updater for sending response
        """
        # Create summary
        summary = self.formatter.create_summary(
            agent_name="LlamaIndexVectorRAG",
            action="completed retrieval-augmented generation",
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
                name="Retrieved Context",
                artifact_id="retrieved-context"
            )


class LlamaIndexVectorRAGAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for LlamaIndex Vector RAG agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define RAG-specific skills."""
        return [
            AgentSkill(
                id="vector-retrieval",
                name="Vector-based Retrieval",
                description="Retrieves relevant documents using vector similarity search with LlamaIndex",
                tags=["rag", "retrieval", "vectors", "similarity", "llamaindex"],
                examples=[
                    "Find relevant documentation about a specific topic",
                    "Retrieve code examples from the knowledge base",
                    "Search for similar issues or solutions"
                ]
            ),
            AgentSkill(
                id="augmented-generation",
                name="Augmented Response Generation",
                description="Generates responses augmented with retrieved context using LlamaIndex",
                tags=["generation", "augmented", "context-aware", "rag", "llamaindex"],
                examples=[
                    "Answer questions based on documentation",
                    "Generate code explanations with examples",
                    "Provide contextual recommendations"
                ]
            )
        ]


def create_llama_index_vector_rag_a2a_app(
    rag_agent: LlamaIndexVectorRAGAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the LlamaIndex Vector RAG agent.
    
    Args:
        rag_agent: The GenPod RAG agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("llama_index_vector_rag")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("LlamaIndex Vector RAG agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = LlamaIndexVectorRAGA2AExecutor(rag_agent)
    
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
        LlamaIndexVectorRAGAgentCardBuilder("LlamaIndexVectorRAG", "1.0.0")
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
        title="GenPod LlamaIndex Vector RAG Agent (A2A)",
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
            "agent": "llama_index_vector_rag",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app