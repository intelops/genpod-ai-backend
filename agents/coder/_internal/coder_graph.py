"""
Coder Graph
"""
from langgraph.graph import END, StateGraph

from agents.coder._internal.coder_node_enum import CoderNodeEnum
from agents.coder._internal.coder_state import (CoderInput, CoderOutput,
                                                CoderState)
from agents.coder._internal.coder_work_flow import CoderWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class CoderGraph(BaseGraph[CoderWorkFlow]):
    """
    Graph representation for the coder workflow.

    This class defines the state graph for a coder workflow. It sets up nodes representing each
    step of the workflow, along with the corresponding edges, conditional transitions, and
    entry/exit points.
    """
    def __init__(
        self,
        work_flow: CoderWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initializes the CoderGraph.

        Args:
            work_flow (CoderWorkFlow): The coder workflow instance containing all workflow nodes.
            recursion_limit (int): The recursion limit for processing the graph.
            persistence_db_path (str): Path to the persistence database.
        """
        super().__init__(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "Initialized CoderGraph with recursion_limit=%d and persistence_db_path='%s'.",
            recursion_limit,
            persistence_db_path
        )

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the coder workflow.

        This method sets up the state graph with nodes corresponding to each step in the coder workflow,
        adds edges and conditional edges to define the transitions between nodes, and sets the entry and exit points.

        Returns:
            StateGraph: The fully defined state graph representing the coder workflow.
        """
        coder_work_flow = StateGraph(CoderState, input=CoderInput, output=CoderOutput)
        logger.debug("Created StateGraph for CoderGraph.")

        nodes = {
            CoderNodeEnum.ENTRY: self.work_flow.entry_node,
            CoderNodeEnum.CODE_GENERATION: self.work_flow.generate_code_node,
            CoderNodeEnum.CODE_GENERATION_FROM_SKELETON: self.work_flow.generate_code_from_skeletons_node,
            CoderNodeEnum.WRITE_GENERATED_CODE: self.work_flow.write_generated_code_node,
            CoderNodeEnum.ADD_LICENSE: self.work_flow.add_license_text_node,
            CoderNodeEnum.DOWNLOAD_LICENSE: self.work_flow.download_license_node,
            CoderNodeEnum.RESOLVE_ISSUE: self.work_flow.resolve_issue_node,
            CoderNodeEnum.EXIT: self.work_flow.exit_node,
        }
        for node_name, node_function in nodes.items():
            coder_work_flow.add_node(str(node_name), node_function)
            logger.debug("Added node: %s", node_name)


        coder_work_flow.add_conditional_edges(
            str(CoderNodeEnum.ENTRY),
            self.work_flow.router,
            {
                str(CoderNodeEnum.CODE_GENERATION): str(CoderNodeEnum.CODE_GENERATION),
                str(CoderNodeEnum.CODE_GENERATION_FROM_SKELETON): str(CoderNodeEnum.CODE_GENERATION_FROM_SKELETON),
                str(CoderNodeEnum.RESOLVE_ISSUE): str(CoderNodeEnum.RESOLVE_ISSUE),
                str(CoderNodeEnum.EXIT): str(CoderNodeEnum.EXIT),
            }
        )

        coder_work_flow.add_edge(
            str(CoderNodeEnum.CODE_GENERATION),
            str(CoderNodeEnum.WRITE_GENERATED_CODE)
        )

        coder_work_flow.add_edge(
            str(CoderNodeEnum.CODE_GENERATION_FROM_SKELETON),
            str(CoderNodeEnum.WRITE_GENERATED_CODE)
        )

        coder_work_flow.add_edge(
            str(CoderNodeEnum.RESOLVE_ISSUE),
            str(CoderNodeEnum.WRITE_GENERATED_CODE)
        )

        coder_work_flow.add_edge(
            str(CoderNodeEnum.WRITE_GENERATED_CODE),
            str(CoderNodeEnum.ADD_LICENSE)
        )

        coder_work_flow.add_conditional_edges(
            str(CoderNodeEnum.ADD_LICENSE),
            self.work_flow.router,
            {
                str(CoderNodeEnum.DOWNLOAD_LICENSE): str(CoderNodeEnum.DOWNLOAD_LICENSE),
                str(CoderNodeEnum.EXIT): str(CoderNodeEnum.EXIT),
            }
        )

        coder_work_flow.add_edge(
            str(CoderNodeEnum.DOWNLOAD_LICENSE),
            str(CoderNodeEnum.EXIT)
        )

        coder_work_flow.set_entry_point(str(CoderNodeEnum.ENTRY))
        coder_work_flow.set_finish_point(str(CoderNodeEnum.EXIT))

        logger.debug("Set entry point to ENTRY and finish point to EXIT.")
        return coder_work_flow
