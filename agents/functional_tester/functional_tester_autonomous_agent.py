"""
Autonomous Functional Tester Agent

This agent uses TaskMaster and autonomous decision-making for functional test generation.
"""


from agents.functional_tester._internal.functional_tester_autonomous_graph import (
    AutonomousFunctionalTesterGraph
)
from agents.functional_tester._internal.functional_tester_autonomous_workflow import (
    AutonomousFunctionalTesterWorkFlow
)
from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class AutonomousFunctionalTesterAgent(BaseAgent[AutonomousFunctionalTesterGraph]):
    """
    Autonomous agent for functional test generation.
    
    This agent:
    - Analyzes tasks to determine if functional testing is needed
    - Uses TaskMaster to break down complex tasks
    - Executes atomic tasks autonomously
    - Makes decisions based on context rather than fixed stages
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str,
        use_rag: bool = False,
        use_mcp: bool = True
    ):
        """
        Initialize the autonomous functional tester agent.
        
        Args:
            id: Unique identifier for the agent
            name: Name of the agent
            description: Agent description
            llm: Language model instance
            recursion_limit: Maximum recursion depth
            persistence_db_path: Path to persistence database
            use_rag: Whether to use RAG (default: False)
            use_mcp: Whether to use MCP/TaskMaster (default: True)
        """
        logger.debug(
            "Initializing AutonomousFunctionalTesterAgent | ID: %s | Name: %s | "
            "Recursion Limit: %d | MCP Enabled: %s",
            id, name, recursion_limit, use_mcp
        )
        
        # Create autonomous workflow
        work_flow = AutonomousFunctionalTesterWorkFlow(id, name, llm, use_rag)
        logger.debug("AutonomousFunctionalTesterWorkFlow initialized for agent: %s", name)
        
        # Create autonomous graph
        graph = AutonomousFunctionalTesterGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "AutonomousFunctionalTesterGraph created for agent: %s",
            name
        )
        
        # Store MCP flag for potential use
        self.use_mcp = use_mcp
        
        super().__init__(id, name, description, llm, graph, use_rag)
        
        logger.info(
            "AutonomousFunctionalTesterAgent successfully initialized | ID: %s | Name: %s",
            id, name
        )
    
    def get_capabilities(self) -> dict:
        """
        Get agent capabilities.
        
        Returns:
            Dictionary of agent capabilities
        """
        return {
            "autonomous": True,
            "uses_taskmaster": self.use_mcp,
            "supports_task_breakdown": True,
            "dynamic_workflow": True,
            "framework_agnostic": True,
            "adaptive_test_generation": True,
            "description": (
                "This agent adapts to any testing framework or library based on project context. "
                "It analyzes the codebase, detects existing patterns, and generates tests using "
                "the most appropriate tools - whether that's pytest, jest, junit, or any other "
                "testing framework. No predetermined choices - pure adaptation."
            )
        }