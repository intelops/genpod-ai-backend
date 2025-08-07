from typing import List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from agents.langchain_vector_rag._internal.langchain_vector_rag_modes import (
    QueryAnswerStage, RAGMode)
from agents.langchain_vector_rag._internal.langchain_vector_rag_nodes import \
    RAGNodeEnum
from agents.langchain_vector_rag._internal.langchain_vector_rag_prompt import \
    RAGPrompts
from agents.langchain_vector_rag._internal.langchain_vector_rag_state import (
    RAGOutput, RAGState)
from apis.rag_analytics.controller import RAGAnalyticsController
from context.context import GenpodContext
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from database.entities.rag_analytics import RAGAnalytics
from llms.llm import LLM
from models import BinaryScore, PromptResponse, RagResponseType, Status
from utils.logger import logger

RAG_RETRY_LIMIT = 1
MAX_HALLUCINATION_LIMIT = 3


class RAGWorkFlow(BaseWorkFlow[RAGPrompts]):
    """
    RAGWorkFlow implements a Retrieval-Augmented Generation (RAG) process that handles a query by
    retrieving relevant documents, grading them, generating an answer, and then grading the answer to
    ensure that it is both grounded in the documents and addresses the query. The workflow supports
    retries and query transformation if necessary.
    
    Workflow stages:
        - ENTRY: Initialize state.
        - RETRIEVE_DOCUMENTS: Retrieve documents from a vector store.
        - GRADE_DOCUMENTS: Grade document relevance.
        - TRANSFORM_QUERY: Transform the query when no relevant documents or answer issues are detected.
        - GENERATE_RESPONSE: Generate a response using the LLM.
        - GRADE_RESPONSE: Grade the generated response for hallucinations and answer quality.
        - EXIT: Finalize and record analytics.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        collection_name: str,
        persist_directory: str
    ):
        """
        Initializes the RAGWorkFlow.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name of the agent.
            llm (LLM): The language model to be used for generation and grading.
            collection_name (str): Name of the vector store collection.
            persist_directory (str): Directory where the vector store is persisted.
        """
        super().__init__(
            agent_id,
            agent_name,
            RAGPrompts(),
            llm
        )

        self._genpod_context = GenpodContext.get_context()
        self._vector_store = Chroma(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=OpenAIEmbeddings()
        )

    def retrieve(self, query: str, n: int) -> List[Document]:
        """
        Retrieve documents from the vector store for a given query.

        Args:
            query (str): The search query.
            n (int): The number of documents to retrieve.

        Returns:
            List[Document]: A list of retrieved Document objects.
        """
        retriever = self._vector_store.as_retriever(search_kwargs={'k': n})
        documents = retriever.invoke(query)
        logger.debug("Retrieved %d documents for query: '%s'.", len(documents), query)
        return documents

    @route_on_errors
    def router(self, state: RAGState) -> str:
        """
        Determines the next node in the workflow based on the current operational mode and stage.

        Args:
            state (RAGState): The current state of the RAG workflow.

        Returns:
            str: The identifier of the next workflow node.
        """
        if state.operational_mode == RAGMode.ANSWER_QUERY:
            stage_to_node = {
                QueryAnswerStage.RETRIEVE_DOCUMENTS: RAGNodeEnum.RETRIEVE_DOCUMENTS,
                QueryAnswerStage.GRADE_DOCUMENTS: RAGNodeEnum.GRADE_DOCUMENTS,
                QueryAnswerStage.GENERATE_RESPONSE: RAGNodeEnum.GENERATE_RESPONSE,
                QueryAnswerStage.TRANSFORM_QUERY: RAGNodeEnum.TRANSFORM_QUERY,
                QueryAnswerStage.GRADE_RESPONSE: RAGNodeEnum.GRADE_RESPONSE,
                QueryAnswerStage.FINISHED: RAGNodeEnum.EXIT
            }
            next_node = stage_to_node.get(state.current_mode_stage, RAGNodeEnum.EXIT)
            if next_node == RAGNodeEnum.EXIT and state.current_mode_stage not in stage_to_node:
                logger.warning("Unrecognized mode stage '%s'. Defaulting to EXIT.", state.current_mode_stage)
            return str(next_node)

        logger.warning("Unrecognized operational mode '%s'. Defaulting to EXIT.", state.operational_mode)
        return str(RAGNodeEnum.EXIT)

    @record_node(RAGNodeEnum.ENTRY)
    def entry_node(self, state: RAGState) -> RAGState:
        """
        Entry node: Initializes the state for processing a query.

        Sets the operational mode to ANSWER_QUERY and the stage to RETRIEVE_DOCUMENTS.

        Args:
            state (RAGState): The current state of the RAG workflow.

        Returns:
            RAGState: The updated state ready for document retrieval.
        """
        func_name = "entry_node"
        logger.info("%s: Initializing workflow state for query processing.", func_name)

        state.operational_mode = RAGMode.ANSWER_QUERY
        state.current_mode_stage = QueryAnswerStage.RETRIEVE_DOCUMENTS

        logger.info(
            "%s: Set operational_mode='%s' and current_mode_stage='%s'.",
            func_name, state.operational_mode, state.current_mode_stage
        )
        return state

    @record_node(RAGNodeEnum.RETRIEVE_DOCUMENTS)
    @handle_errors_and_reset
    def retrieve_documents_node(self, state: RAGState) -> RAGState:
        """
        Node for retrieving documents relevant to the query.

        Retrieves documents from the vector store and advances the state to the document grading stage.

        Args:
            state (RAGState): The current workflow state containing the query.

        Returns:
            RAGState: The state updated with retrieved documents and stage set to GRADE_DOCUMENTS.
        """
        func_name = "retrieve_documents_node"
        logger.info("%s: Retrieving documents for query: '%s'.", func_name, state.query)

        documents = self.retrieve(state.query, 20)
        logger.info("%s: Retrieved %d documents.", func_name, len(documents))

        state.documents = documents
        state.current_mode_stage = QueryAnswerStage.GRADE_DOCUMENTS
        logger.info("%s: Transitioned to stage '%s'.", func_name, state.current_mode_stage)
        return state


    @record_node(RAGNodeEnum.GRADE_DOCUMENTS)
    @handle_errors_and_reset
    def grade_documents_node(self, state: RAGState) -> RAGState:
        """
        Node for grading the relevance of retrieved documents.

        Evaluates each document using the retriever grader prompt. Only documents that score as
        relevant (binary score True) are retained. If no documents pass the relevance test, the workflow
        transitions to query transformation.

        Args:
            state (RAGState): The current state containing the retrieved documents and query.

        Returns:
            RAGState: The updated state with filtered relevant documents and the next stage set.
        """
        func_name = "grade_documents_node"
        retrieved_documents = state.documents
        total_documents = len(retrieved_documents)
        logger.info("%s: Grading %d documents for relevance to query: '%s'.", func_name, total_documents, state.query)

        filtered_documents = []
        for idx, document in enumerate(retrieved_documents, start=1):
            logger.debug("%s: Grading document %d of %d.", func_name, idx, total_documents)
            graded_output = self.invoke_with_pydantic_model(
                self.prompts.retriever_grader_prompt,
                {'question': state.query, 'document': document.page_content},
                BinaryScore
            )
            grade = graded_output.response.score
            if not grade:
                logger.debug("%s: Document %d deemed not relevant.", func_name, idx)
                continue

            logger.debug("%s: Document %d deemed relevant.", func_name, idx)
            filtered_documents.append(document)

        logger.info("%s: %d out of %d documents passed relevance grading.", func_name, len(filtered_documents), total_documents)
        if not filtered_documents:
            logger.info("%s: No relevant documents found. Transitioning to TRANSFORM_QUERY stage.", func_name)
            state.current_mode_stage = QueryAnswerStage.TRANSFORM_QUERY
        else:
            state.documents = filtered_documents
            state.current_mode_stage = QueryAnswerStage.GENERATE_RESPONSE
            logger.info("%s: Retained relevant documents. Transitioning to GENERATE_RESPONSE stage.", func_name)

        return state

    @record_node(RAGNodeEnum.TRANSFORM_QUERY)
    @handle_errors_and_reset
    def transform_query_node(self, state: RAGState) -> RAGState:
        """
        Node for transforming the query when retrieval or answer generation fails.

        Invokes the LLM with a rewrite prompt to generate an improved query. Increments the retry count
        and resets the stage to RETRIEVE_DOCUMENTS if the retry limits have not been exceeded.

        Args:
            state (RAGState): The current state with the original query.

        Returns:
            RAGState: The updated state with the transformed query and stage reset.
        """
        func_name = "transform_query_node"
        logger.info("%s: Received query for transformation: '%s'.", func_name, state.query)

        retry_allowed, updated_state = self._check_retry_limits(state)
        if not retry_allowed:
            logger.info("%s: Retry limits exceeded. No further query transformation attempted.", func_name)
            return updated_state

        llm_output = self.invoke(
            self.prompts.re_write_prompt,
            {'question': state.query},
            'string'
        )
        transformed_query = llm_output.response
        logger.info("%s: Transformed query: '%s'.", func_name, transformed_query)

        state.query = transformed_query
        state.retry_count += 1
        state.current_mode_stage = QueryAnswerStage.RETRIEVE_DOCUMENTS
        logger.info("%s: Retry count incremented to %d. Restarting retrieval stage.", func_name, state.retry_count)
        return state

    @record_node(RAGNodeEnum.GENERATE_RESPONSE)
    @handle_errors_and_reset
    def generate_response_node(self, state: RAGState) -> RAGState:
        """
        Node for generating an answer to the query using retrieved documents as context.

        Invokes the LLM generation prompt with the current query and document context. The generated answer
        is then evaluated for quality (i.e. whether it is unknown or a valid answer).

        Args:
            state (RAGState): The current state containing the query and documents.

        Returns:
            RAGState: The state updated with the generated response and set to the grading stage.
        """
        func_name = "generate_response_node"
        logger.info("%s: Generating response for query: '%s'.", func_name, state.query)

        texts = [doc.page_content for doc in state.documents]
        context_str = "\n\n---\n\n".join(texts)
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.rag_generation_prompt,
            {'question': state.query, 'context': context_str},
            PromptResponse
        )
        prompt_response = llm_output.response
        logger.debug("%s: LLM generated response: '%s'.", func_name, prompt_response.response)

        if prompt_response.is_unknown:
            logger.info("%s: LLM indicated an unknown response. Marking as NOT_ANSWERED.", func_name)
            state.response = ""
            state.response_type = RagResponseType.NOT_ANSWERED
            state.current_mode_stage = QueryAnswerStage.TRANSFORM_QUERY
            return state

        logger.info("%s: Valid response generated. Marking as ANSWERED.", func_name)
        state.response_type = RagResponseType.ANSWERED

        state.response = prompt_response.response
        state.current_mode_stage = QueryAnswerStage.GRADE_RESPONSE
        logger.info("%s: Transitioning to GRADE_RESPONSE stage.", func_name)
        return state

    @record_node(RAGNodeEnum.GRADE_RESPONSE)
    @handle_errors_and_reset
    def grade_response_node(self, state: RAGState) -> RAGState:
        """
        Node for grading the generated response for hallucination and overall answer quality.

        First, it invokes the hallucination grader prompt to ensure that the response is grounded in the provided
        documents. If the response is deemed hallucinated, the hallucination counter is incremented and, if within limits,
        the workflow will retry generation. Otherwise, the answer grader prompt is invoked to verify that the response
        adequately answers the query. Failure in the answer grading transitions the workflow to query transformation.

        Args:
            state (RAGState): The current state containing the generated response, query, and documents.

        Returns:
            RAGState: The updated state with an appropriate next stage based on the grading outcome.
        """
        func_name = "grade_response_node"
        logger.info("%s: Starting response grading.", func_name)

        texts = [doc.page_content for doc in state.documents]
        facts = "\n\n---\n\n".join(texts)
        # Evaluate for hallucination issues.
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.hallucination_grader_prompt,
            {
                'generation': state.response,
                'documents': facts
            },
            BinaryScore
        )
        hallucination_grade = llm_output.response.score
        logger.info("%s: Hallucination grade: %s.", func_name, hallucination_grade)

        if not hallucination_grade:
            logger.info("%s: Response failed the hallucination check.", func_name)
            state.hallucination_count += 1
            logger.debug("%s: Updated hallucination_count to %d, retry_count remains %d.", func_name,
                         state.hallucination_count, state.retry_count)

            if state.hallucination_count < MAX_HALLUCINATION_LIMIT:
                logger.info("%s: Retrying response generation. Reverting to GENERATE_RESPONSE stage.", func_name)
                state.response = ""
                state.response_type = RagResponseType.NOT_ADDRESSED
                state.current_mode_stage = QueryAnswerStage.GENERATE_RESPONSE
            else:
                logger.info("%s: Maximum hallucination attempts reached. Rejecting response.", func_name)
                state.response = ""
                state.response_type = RagResponseType.REJECTED
                state.current_mode_stage = QueryAnswerStage.FINISHED

            return state

        # Evaluate overall answer quality.
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.answer_grader_prompt,
            {
                'question': state.query,
                'generation': state.response
            },
            BinaryScore
        )
        response_grade = llm_output.response.score
        logger.info("%s: Answer quality grade: %s.", func_name, response_grade)

        if not response_grade:
            logger.info("%s: Generated response does not adequately answer the query. Transitioning to TRANSFORM_QUERY stage.", func_name)
            state.current_mode_stage = QueryAnswerStage.TRANSFORM_QUERY
            state.response_type = RagResponseType.NOT_ADDRESSED
            state.response = ""
        else:
            logger.info("%s: Response passed grading. Marking workflow as FINISHED.", func_name)
            state.current_mode_stage = QueryAnswerStage.FINISHED

        return state

    @record_node(RAGNodeEnum.EXIT)
    def exit_node(self, state: RAGState) -> RAGOutput:
        """
        Exit node: Finalizes the workflow.

        Resets counters, records analytics (if a valid answer was provided), and marks the current task as DONE.

        Args:
            state (RAGState): The final state of the workflow.

        Returns:
            RAGOutput: The final output state.
        """
        func_name = "exit_node"
        logger.info("Agent '%s': %s - Finalizing workflow.", self.agent_name, func_name)
        state.hallucination_count = 0
        state.retry_count = 0

        if state.operational_mode == RAGMode.ANSWER_QUERY and state.response_type == RagResponseType.ANSWERED:
            self._save_analytics_record(state)

        state.current_task.task_status = Status.DONE
        logger.info("Agent '%s': %s - Workflow completed; task marked as DONE.", self.agent_name, func_name)
        return state

    def _save_analytics_record(self, state: RAGState):
        """
        Saves analytics records for each document used in answering the query.

        Creates an analytics record for each document by extracting metadata and other context
        and then saves the record using the RAGAnalyticsController.

        Args:
            state (RAGState): The current state containing documents and query information.
        """
        analytics_ctrl = RAGAnalyticsController()
        # Determine the appropriate agent context.
        agent_context = (self._genpod_context.previous_agent
                         if self._genpod_context.previous_agent
                         else self._genpod_context.current_agent)
        for document in state.documents:
            document_id = document.metadata.get('id', "")
            document_version = document.metadata.get('version', "")

            analytics_record = RAGAnalytics(
                agent_id=agent_context.agent_id,
                project_id=self._genpod_context.project_id,
                application_id=self._genpod_context.application_id,
                session_id=agent_context.agent_session_id,
                task_id=self._genpod_context.current_task.task_id,
                document_id=document_id,
                document_version=document_version,
                question=state.query,
                raw_response=state.response,
                size_of_data=len(state.response),
                created_by=self._genpod_context.user_id,
                updated_by=self._genpod_context.user_id
            )
            analytics_ctrl.create(analytics_record)
            logger.debug("Saved analytics record for document id '%s', version '%s'.", document_id, document_version)

    def _check_retry_limits(self, state: RAGState) -> Tuple[bool, RAGState]:
        """
        Checks whether additional retries are allowed based on current retry and hallucination counts.

        If either the retry_count or hallucination_count has reached its limit, the state is updated to
        reflect that no further attempts should be made (typically by marking the response as rejected).

        Args:
            state (RAGState): The current state of the workflow.

        Returns:
            Tuple[bool, RAGState]:
                - bool: True if another retry is allowed, False otherwise.
                - RAGState: The (possibly updated) state.
        """
        if state.retry_count < RAG_RETRY_LIMIT and state.hallucination_count < MAX_HALLUCINATION_LIMIT:
            return True, state
        else:
            logger.info(
                "Retry limits reached (retry_count=%d, hallucination_count=%d). No further attempts will be made.",
                state.retry_count, state.hallucination_count
            )
            state.current_mode_stage = QueryAnswerStage.FINISHED
            state.response_type = RagResponseType.REJECTED
            state.response = ""
            return False, state
