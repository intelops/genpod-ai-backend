from langgraph.graph import StateGraph

from agents.langchain_vector_rag._internal.langchain_vector_rag_nodes import \
    RAGNodeEnum
from agents.langchain_vector_rag._internal.langchain_vector_rag_state import (
    RAGInput, RAGOutput, RAGState)
from agents.langchain_vector_rag._internal.langchain_vector_rag_work_flow import \
    RAGWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class RAGGraph(BaseGraph[RAGWorkFlow]):
    """
    Graph representation for the Retrieval-Augmented Generation (RAG) workflow.

    This class defines the state transitions for the RAG workflow by creating nodes and
    conditional edges. Each node corresponds to a specific stage in the workflow, and the
    transitions are determined by the router function from the RAGWorkFlow instance.
    
    The entry point is set to RAGNodeEnum.ENTRY and the finish point is set to RAGNodeEnum.EXIT.
    """

    def __init__(
        self,
        work_flow: RAGWorkFlow, 
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initialize the RAGGraph with a given workflow, recursion limit, and persistence database path.

        Args:
            work_flow (RAGWorkFlow): An instance of the RAG workflow.
            recursion_limit (int): Maximum recursion depth allowed for the graph transitions.
            persistence_db_path (str): Path to the database for persisting the graph state.
        """
        super().__init__(work_flow, recursion_limit, persistence_db_path)
        logger.info(
            "Initialized RAGGraph with recursion_limit=%d and persistence_db_path='%s'.",
            recursion_limit, persistence_db_path
        )

    def define_graph(self):
        """
        Define and return the state graph for the RAG workflow.

        The graph is built using nodes corresponding to the various stages of the workflow and
        conditional edges that dictate state transitions based on the router's output.

        Returns:
            StateGraph: The fully defined state graph for the RAG workflow.
        """
        logger.info("Defining the RAG workflow graph...")
        rag_work_flow_graph = StateGraph(RAGState, input=RAGInput, output=RAGOutput)

        node_mapping = {
            RAGNodeEnum.ENTRY: self.work_flow.entry_node,
            RAGNodeEnum.RETRIEVE_DOCUMENTS: self.work_flow.retrieve_documents_node,
            RAGNodeEnum.GRADE_DOCUMENTS: self.work_flow.grade_documents_node,
            RAGNodeEnum.TRANSFORM_QUERY: self.work_flow.transform_query_node,
            RAGNodeEnum.GENERATE_RESPONSE: self.work_flow.generate_response_node,
            RAGNodeEnum.GRADE_RESPONSE: self.work_flow.grade_response_node,
            RAGNodeEnum.EXIT: self.work_flow.exit_node,
        }

        for node, func in node_mapping.items():
            node_str = str(node)
            rag_work_flow_graph.add_node(node_str, func)
            logger.debug("Added node '%s' to the graph.", node_str)

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.ENTRY),
            self.work_flow.router,
            {
                str(RAGNodeEnum.RETRIEVE_DOCUMENTS): str(RAGNodeEnum.RETRIEVE_DOCUMENTS),
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.ENTRY))

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.RETRIEVE_DOCUMENTS),
            self.work_flow.router, 
            {
                str(RAGNodeEnum.GRADE_DOCUMENTS): str(RAGNodeEnum.GRADE_DOCUMENTS),
                str(RAGNodeEnum.RETRIEVE_DOCUMENTS): str(RAGNodeEnum.RETRIEVE_DOCUMENTS),
                str(RAGNodeEnum.EXIT): str(RAGNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.RETRIEVE_DOCUMENTS))

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.GRADE_DOCUMENTS),
            self.work_flow.router, 
            {
                str(RAGNodeEnum.GRADE_DOCUMENTS): str(RAGNodeEnum.GRADE_DOCUMENTS),
                str(RAGNodeEnum.TRANSFORM_QUERY): str(RAGNodeEnum.TRANSFORM_QUERY),
                str(RAGNodeEnum.GENERATE_RESPONSE): str(RAGNodeEnum.GENERATE_RESPONSE)
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.GRADE_DOCUMENTS))

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.TRANSFORM_QUERY),
            self.work_flow.router,
            {
                str(RAGNodeEnum.TRANSFORM_QUERY): str(RAGNodeEnum.TRANSFORM_QUERY),
                str(RAGNodeEnum.RETRIEVE_DOCUMENTS): str(RAGNodeEnum.RETRIEVE_DOCUMENTS),
                str(RAGNodeEnum.EXIT): str(RAGNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.TRANSFORM_QUERY))

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.GENERATE_RESPONSE),
            self.work_flow.router,
            {
                str(RAGNodeEnum.GENERATE_RESPONSE): str(RAGNodeEnum.GENERATE_RESPONSE),
                str(RAGNodeEnum.TRANSFORM_QUERY): str(RAGNodeEnum.TRANSFORM_QUERY),
                str(RAGNodeEnum.GRADE_RESPONSE): str(RAGNodeEnum.GRADE_RESPONSE),
                str(RAGNodeEnum.EXIT): str(RAGNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.GENERATE_RESPONSE))

        rag_work_flow_graph.add_conditional_edges(
            str(RAGNodeEnum.GRADE_RESPONSE),
            self.work_flow.router,
            {
                str(RAGNodeEnum.GRADE_RESPONSE): str(RAGNodeEnum.GRADE_RESPONSE),
                str(RAGNodeEnum.GENERATE_RESPONSE): str(RAGNodeEnum.GENERATE_RESPONSE),
                str(RAGNodeEnum.TRANSFORM_QUERY): str(RAGNodeEnum.TRANSFORM_QUERY),
                str(RAGNodeEnum.EXIT): str(RAGNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges for node '%s'.", str(RAGNodeEnum.GRADE_RESPONSE))

        rag_work_flow_graph.set_entry_point(RAGNodeEnum.ENTRY)
        rag_work_flow_graph.set_finish_point(RAGNodeEnum.EXIT)
        logger.info("Set graph entry point to '%s' and finish point to '%s'.",
                    RAGNodeEnum.ENTRY, RAGNodeEnum.EXIT)

        logger.info("RAG workflow graph defined successfully.")
        return rag_work_flow_graph
