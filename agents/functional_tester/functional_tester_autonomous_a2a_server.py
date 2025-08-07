"""
A2A Protocol Server for Autonomous Functional Tester Agent

This module wraps the autonomous functional tester agent for A2A protocol exposure.
"""

import asyncio
from typing import List, Optional

from fastapi import FastAPI
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.database_task_store import DatabaseTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentSkill, Message

from agents.functional_tester.functional_tester_autonomous_agent import AutonomousFunctionalTesterAgent
from agents.functional_tester._internal.functional_tester_autonomous_state import (
    AutonomousFunctionalTesterState,
    AutonomousFunctionalTesterInput,
    AutonomousFunctionalTesterOutput
)
from core.a2a import BaseA2AExecutor, A2AConfigLoader, A2AExecutionError
from core.a2a.base.agent_card import BaseAgentCardBuilder
from core.a2a.utils import MessageExtractor, ResponseFormatter
from utils.logger import logger


class AutonomousFunctionalTesterA2AExecutor(
    BaseA2AExecutor[AutonomousFunctionalTesterAgent, AutonomousFunctionalTesterInput, AutonomousFunctionalTesterOutput]
):
    """
    A2A executor for the autonomous functional tester agent.
    """
    
    def __init__(self, functional_tester_agent: AutonomousFunctionalTesterAgent):
        """
        Initialize the autonomous functional tester A2A executor.
        
        Args:
            functional_tester_agent: The autonomous agent instance
        """
        super().__init__(functional_tester_agent, "AutonomousFunctionalTester")
        self.extractor = MessageExtractor()
        self.formatter = ResponseFormatter()
    
    async def _extract_input(self, message: Optional[Message]) -> AutonomousFunctionalTesterInput:
        """
        Extract and validate input from A2A message.
        
        Args:
            message: The A2A message
            
        Returns:
            Validated input instance
        """
        try:
            # Extract input
            test_input = self.extractor.extract_agent_input(
                message=message,
                input_model=AutonomousFunctionalTesterInput,
                field_name="agent_input"
            )
            
            # Validation
            if not test_input.project_name:
                raise ValueError("project_name is required")
            
            if not test_input.current_planned_task:
                raise ValueError("current_planned_task is required")
            
            logger.debug(
                f"[A2A-AutonomousFunctionalTester] Extracted input for project: {test_input.project_name}"
            )
            return test_input
            
        except Exception as e:
            logger.error(f"[A2A-AutonomousFunctionalTester] Input extraction failed: {str(e)}")
            raise
    
    async def _execute_agent(
        self, 
        agent_input: AutonomousFunctionalTesterInput, 
        task_id: str
    ) -> AutonomousFunctionalTesterOutput:
        """
        Execute the autonomous agent with given input.
        
        Args:
            agent_input: Validated input
            task_id: Current task ID
            
        Returns:
            Output containing results
        """
        try:
            # Create initial state
            initial_state = AutonomousFunctionalTesterState(**agent_input.model_dump())
            
            # Run the autonomous agent
            logger.info(
                f"[A2A-AutonomousFunctionalTester] Executing autonomous workflow for task {task_id}"
            )
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.to_thread(
                self.agent.graph.invoke,
                initial_state.model_dump()
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"[A2A-AutonomousFunctionalTester] Task {task_id} completed in {execution_time:.2f} seconds"
            )
            
            # Create output with execution summary
            output = AutonomousFunctionalTesterOutput(**result)
            output.execution_summary = {
                "task_id": task_id,
                "execution_time": execution_time,
                "atomic_tasks_count": len(output.atomic_tasks_executed),
                "files_generated": len(output.functional_test_code),
                "scenarios_generated": len(output.test_scenarios)
            }
            
            return output
            
        except Exception as e:
            logger.error(
                f"[A2A-AutonomousFunctionalTester] Failed to execute agent: {str(e)}", 
                exc_info=True
            )
            raise A2AExecutionError(f"Autonomous execution failed: {str(e)}")
    
    async def _format_response(
        self, 
        agent_output: AutonomousFunctionalTesterOutput, 
        updater: TaskUpdater
    ) -> None:
        """
        Format output and send response.
        
        Args:
            agent_output: Output from the agent
            updater: Task updater for sending response
        """
        # Create summary
        summary = self.formatter.create_summary(
            agent_name="AutonomousFunctionalTester",
            action="completed autonomous functional test generation",
            details={
                "task_status": agent_output.current_planned_task.task_status.value,
                "atomic_tasks_executed": len(agent_output.atomic_tasks_executed),
                "test_files": len(agent_output.functional_test_code),
                "scenarios": len(agent_output.test_scenarios),
                "execution_time": agent_output.execution_summary.get("execution_time", "N/A")
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
        if agent_output.test_scenarios:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.test_scenarios,
                name="Test Scenarios",
                artifact_id="test-scenarios"
            )
        
        if agent_output.functional_test_code:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.functional_test_code,
                name="Functional Test Code",
                artifact_id="functional-test-code"
            )
        
        if agent_output.atomic_tasks_executed:
            await self.formatter.add_artifact(
                updater=updater,
                data=agent_output.atomic_tasks_executed,
                name="Execution Log",
                artifact_id="execution-log"
            )


class AutonomousFunctionalTesterAgentCardBuilder(BaseAgentCardBuilder):
    """Agent card builder for autonomous functional tester."""
    
    def _default_skills(self) -> List[AgentSkill]:
        """Define autonomous agent skills."""
        return [
            AgentSkill(
                id="framework-agnostic-generation",
                name="Framework-Agnostic Test Generation",
                description="Adapts to any testing framework based on project context",
                tags=["framework-agnostic", "adaptive", "context-aware", "intelligent"],
                examples=[
                    "Detect Jest in React project and generate Jest tests",
                    "Find pytest in Python project and follow pytest patterns",
                    "Identify JUnit in Java and create JUnit test classes",
                    "Adapt to custom testing frameworks and patterns"
                ]
            ),
            AgentSkill(
                id="pattern-detection",
                name="Project Pattern Detection",
                description="Analyzes codebase to detect testing patterns and conventions",
                tags=["pattern-detection", "code-analysis", "convention-following"],
                examples=[
                    "Detect BDD style (Given/When/Then) and follow it",
                    "Identify TDD patterns and generate tests accordingly",
                    "Match existing test file naming conventions",
                    "Follow project-specific assertion patterns"
                ]
            ),
            AgentSkill(
                id="taskmaster-integration",
                name="TaskMaster Task Breakdown",
                description="Uses TaskMaster MCP to break down complex tasks",
                tags=["taskmaster", "mcp", "task-breakdown", "atomic-tasks"],
                examples=[
                    "Break down 'test user registration' into atomic steps",
                    "Decompose complex test scenarios into manageable tasks",
                    "Create execution plan for test generation"
                ]
            ),
            AgentSkill(
                id="adaptive-execution",
                name="Context-Aware Adaptive Execution",
                description="Learns from the project and adapts test generation approach",
                tags=["adaptive", "learning", "context-aware", "dynamic"],
                examples=[
                    "Learn from existing tests to match style and structure",
                    "Adapt to microservices vs monolithic architectures",
                    "Generate tests that fit the project's tech stack",
                    "Use latest best practices for detected frameworks"
                ]
            )
        ]


def create_autonomous_functional_tester_a2a_app(
    functional_tester_agent: AutonomousFunctionalTesterAgent,
    db_path: str
) -> FastAPI:
    """
    Create FastAPI app with A2A protocol for autonomous functional tester.
    
    Args:
        functional_tester_agent: The autonomous agent instance
        db_path: Path to SQLite database
        
    Returns:
        FastAPI application
    """
    # Load configuration
    config_loader = A2AConfigLoader()
    config = config_loader.load()
    agent_config = config.get_agent_config("functional_tester")
    
    if not agent_config or not agent_config.enabled:
        raise ValueError("Functional Tester agent is not enabled in configuration")
    
    # Create components
    task_store = DatabaseTaskStore(f"sqlite:///{db_path}")
    executor = AutonomousFunctionalTesterA2AExecutor(functional_tester_agent)
    
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        queue_manager=None,
        push_config_store=None,
        push_sender=None,
        request_context_builder=None
    )
    
    # Create agent card
    agent_card = (
        AutonomousFunctionalTesterAgentCardBuilder("AutonomousFunctionalTester", "2.0.0")
        .with_description(
            "Autonomous functional test generation using AI-driven task breakdown and execution"
        )
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
        title="GenPod Autonomous Functional Tester Agent (A2A)",
        description="Autonomous functional test generation with TaskMaster integration",
        version="2.0.0"
    )
    
    # Add routes
    a2a_app.add_routes_to_app(app)
    
    # Health check
    @app.get("/health")
    async def health_check():
        capabilities = functional_tester_agent.get_capabilities()
        return {
            "status": "healthy",
            "agent": "autonomous_functional_tester",
            "protocol": "a2a",
            "version": "2.0.0",
            "capabilities": capabilities
        }
    
    return app
