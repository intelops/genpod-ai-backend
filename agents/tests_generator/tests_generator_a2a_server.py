"""
A2A Protocol Server for Tests Generator Agent

This module wraps the Tests Generator agent to expose it via the A2A (Agent-to-Agent) protocol.
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

from agents.tests_generator.tests_generator_agent import TestsGeneratorAgent
from agents.tests_generator._internal.tests_generator_state import TestCoderState, TestCoderInput, TestCoderOutput
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class TestsGeneratorA2AExecutor(BaseA2AExecutor[TestsGeneratorAgent, TestCoderInput, TestCoderOutput]):
    """
    A2A Protocol executor for the Tests Generator agent.
    
    Implements the abstract methods from BaseA2AExecutor to handle
    tests generator-specific input/output processing.
    """
    
    def __init__(self, tests_generator_agent: TestsGeneratorAgent):
        """
        Initialize the Tests Generator A2A executor.
        
        Args:
            tests_generator_agent: The underlying GenPod Tests Generator agent instance
        """
        super().__init__(tests_generator_agent, "TestsGenerator")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> TestCoderInput:
        """
        Extract and validate tests generator input from A2A message.
        
        Args:
            message: The A2A message containing input
            
        Returns:
            Validated TestCoderInput instance
        """
        try:
            # Extract input using the common extractor
            test_input = self.extractor.extract_agent_input(
                message=message,
                input_model=TestCoderInput,
                field_name="agent_input"
            )
            
            # Additional validation
            if not test_input.project_name:
                raise ValueError("project_name is required")
            
            if not test_input.requirements_document:
                raise ValueError("requirements_document is required")
                
            logger.debug(f"[A2A-TestsGenerator] Extracted input for project: {test_input.project_name}")
            return test_input
            
        except Exception as e:
            logger.error(f"[A2A-TestsGenerator] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(self, agent_input: TestCoderInput, task_id: str) -> TestCoderOutput:
        """
        Execute the tests generator agent with given input.
        
        Args:
            agent_input: Validated input for the tests generator
            task_id: Current task ID
            
        Returns:
            TestCoderOutput containing results
        """
        try:
            # Create initial state from input
            initial_state = TestCoderState(**agent_input.model_dump())
            
            # Run the tests generator agent graph
            logger.info(f"[A2A-TestsGenerator] Executing agent workflow for task {task_id}")
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[A2A-TestsGenerator] Task {task_id} completed in {execution_time:.2f} seconds")
            
            # Create and return output
            return TestCoderOutput(**result)
            
        except Exception as e:
            logger.error(f"[A2A-TestsGenerator] Failed to execute agent: {str(e)}", exc_info=True)
            raise A2AExecutionError(f"Tests Generator execution failed: {str(e)}")
    
    async def _format_response(self, agent_output: TestCoderOutput, updater: TaskUpdater) -> None:
        """
        Format tests generator output and send response.
        
        Args:
            agent_output: Output from the tests generator agent
            updater: Task updater for sending response
        """
        # Create summary
        test_files = len(agent_output.test_code) if agent_output.test_code else 0
        
        summary = self.formatter.create_summary(
            agent_name="TestsGenerator",
            action="completed test generation",
            details={
                "test_files": test_files,
                "task": agent_output.current_planned_task.task_id if agent_output.current_planned_task else "N/A"
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
        if agent_output.test_code:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.test_code,
                name="Generated Test Code",
                artifact_id="test-code"
            )
        
        if agent_output.function_signatures:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.function_signatures,
                name="Function Signatures",
                artifact_id="function-signatures"
            )


class TestsGeneratorAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for Tests Generator agent."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define tests generator-specific skills."""
        return [
            AgentSkill(
                id="test-generation",
                name="Test Code Generation",
                description="Generates comprehensive unit tests for code",
                tags=["testing", "unit-tests", "test-generation", "quality"],
                examples=[
                    "Generate unit tests for a Python module",
                    "Create test cases for API endpoints",
                    "Generate mock-based tests for service layers"
                ]
            ),
            AgentSkill(
                id="test-frameworks",
                name="Test Framework Support",
                description="Supports multiple testing frameworks and patterns",
                tags=["pytest", "unittest", "jest", "mocha", "testing-frameworks"],
                examples=[
                    "Generate pytest tests with fixtures",
                    "Create Jest tests for React components",
                    "Generate JUnit tests for Java classes"
                ]
            )
        ]


def create_tests_generator_a2a_app(
    tests_generator_agent: TestsGeneratorAgent,
    db_path: str
) -> FastAPI:
    """
    Create a FastAPI application with A2A protocol support for the Tests Generator agent.
    
    Args:
        tests_generator_agent: The GenPod Tests Generator agent instance
        db_path: Path to the SQLite database
        
    Returns:
        FastAPI application configured for A2A protocol
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("tests_generator")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Tests Generator agent is not enabled in configuration")
    
    # Create async engine for the database
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    
    # Create task store using the engine
    task_store = DatabaseTaskStore(engine)
    
    # Create agent executor
    executor = TestsGeneratorA2AExecutor(tests_generator_agent)
    
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
        TestsGeneratorAgentCardBuilder("TestsGenerator", "1.0.0")
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
        title="GenPod Tests Generator Agent (A2A)",
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
            "agent": "tests_generator",
            "protocol": "a2a",
            "port": agent_config.port
        }
    
    return app