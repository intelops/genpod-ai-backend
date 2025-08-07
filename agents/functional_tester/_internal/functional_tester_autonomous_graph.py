"""
Autonomous Functional Tester Graph

Simplified graph structure for autonomous functional test generation.
"""

from agents.functional_tester._internal.functional_tester_autonomous_workflow import (
    AutonomousFunctionalTesterWorkFlow
)
from agents.functional_tester._internal.functional_tester_autonomous_state import (
    AutonomousFunctionalTesterState,
    AutonomousFunctionalTesterInput,
    AutonomousFunctionalTesterOutput
)
from core.graph import BaseGraph
from langgraph.constants import END
from langgraph.graph import StateGraph
from utils.logger import logger


class AutonomousFunctionalTesterGraph(BaseGraph):
    """
    Simplified graph for autonomous functional testing.
    
    This graph has minimal nodes:
    - Entry: Initial state setup
    - Process: Main autonomous processing
    - Exit: Final state and cleanup
    """
    
    def __init__(self, work_flow: AutonomousFunctionalTesterWorkFlow, recursion_limit: int, persistence_db_path: str):
        """
        Initialize the autonomous functional tester graph.
        
        Args:
            work_flow: The autonomous workflow instance
            recursion_limit: Maximum recursion depth
            persistence_db_path: Path to persistence database
        """
        logger.debug(
            "Initializing AutonomousFunctionalTesterGraph with recursion_limit=%d",
            recursion_limit
        )
        
        super().__init__(work_flow, recursion_limit, persistence_db_path)
        
        logger.info("AutonomousFunctionalTesterGraph initialized successfully")
    
    def define_graph(self) -> StateGraph:
        """
        Define the simplified autonomous graph.
        
        Returns:
            StateGraph: The defined state graph
        """
        logger.debug("Defining autonomous functional tester graph")
        
        # Initialize graph with proper state classes
        graph = StateGraph(
            AutonomousFunctionalTesterState,
            input=AutonomousFunctionalTesterInput,
            output=AutonomousFunctionalTesterOutput
        )
        
        # Add minimal nodes
        graph.add_node("entry", self.work_flow.entry_node)
        graph.add_node("process", self.work_flow.process_task)
        graph.add_node("exit", self.work_flow.exit_node)
        
        # Set entry point
        graph.set_entry_point("entry")
        
        # Add edges
        graph.add_conditional_edges(
            "entry",
            self.work_flow.router,
            {
                "process": "process",
                "exit": "exit"
            }
        )
        
        graph.add_conditional_edges(
            "process",
            self.work_flow.router,
            {
                "process": "process",  # Can loop if needed
                "exit": "exit"
            }
        )
        
        graph.add_edge("exit", END)
        
        logger.info("Autonomous graph definition complete")
        return graph