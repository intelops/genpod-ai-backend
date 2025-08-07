from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Literal, Type, TypeVar, Union

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from core.decorators import rag_query_handler
from core.prompt import BasePrompt
from llms import LLM, LLMOutput
from utils.decorators import auto_repr
from utils.logger import logger

GenericAgentPrompt = TypeVar('GenericAgentPrompt')
TResponse = TypeVar('TResponse', bound=BaseModel)


@auto_repr
class BaseWorkFlow(ABC, Generic[GenericAgentPrompt]):
    """
    Abstract base class for all agent workflows, implementing common functionalities.
    
    Subclasses must implement the `router` method to determine the routing logic 
    based on the current state.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        prompts: GenericAgentPrompt,
        llm: LLM,
        use_rag: bool = False
    ) -> None:
        """
        Initializes the BaseWorkFlow.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name for the agent.
            prompts (GenericAgentPrompt): The prompts used by the agent.
            llm (LLM): Instance of a Language Learning Model.
            use_rag (bool, optional): Flag to enable RAG interactions. Defaults to False.
        """

        logger.info(f"Initializing {self.__class__.__name__} with agent_id='{agent_id}' and agent_name='{agent_name}'")
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.prompts = prompts
        self.llm = llm  # Public access for MCP and other components
        self.use_rag = use_rag
        logger.info(f"Initialized {self.__class__.__name__} successfully.")

    @abstractmethod
    def router(self, state: Any) -> str:
        """
        Determines the routing logic based on the agent's current state.

        Args:
            state (Any): The current state of the agent. (Consider replacing `Any` 
                         with a more specific type, such as a subclass of BaseState.)

        Returns:
            str: The routing decision or response.
        """
        pass

    @rag_query_handler
    def invoke(
        self,
        prompt: BasePrompt,
        prompt_inputs: Dict[str, Any],
        response_type: Literal['string', 'json', 'raw'] = 'raw'
    ) -> LLMOutput[Union[str, dict, AIMessage]]:
        """
        Invokes the underlying language model with the provided prompt and inputs.

        Args:
            prompt (BasePrompt): The prompt configuration to use.
            prompt_inputs (Dict[str, Any]): The inputs to be passed to the prompt.
            response_type (Literal['string', 'json', 'raw'], optional): The expected type of the response.
                                                                          Defaults to 'raw'.

        Returns:
            LLMOutput[Union[str, dict, AIMessage]]: The output from the language model.
        """
        logger.debug(f"Invoking LLM with prompt: {prompt}, inputs: {prompt_inputs}, response_type: {response_type}")
        output = self.llm.invoke(prompt, prompt_inputs, response_type)
        logger.debug(f"LLM invocation completed with output: {output}")
        return output

    @rag_query_handler
    def invoke_with_pydantic_model(
        self,
        prompt: BasePrompt,
        prompt_inputs: Dict[str, Any],
        response_model: Type[TResponse]
    ) -> LLMOutput[TResponse]:
        """
        Invokes the underlying language model using a pydantic model to parse the response.

        Args:
            prompt (BasePrompt): The prompt configuration to use.
            prompt_inputs (Dict[str, Any]): The inputs to be passed to the prompt.
            response_model (Type[TResponse]): A Pydantic model class that defines the expected response schema.

        Returns:
            LLMOutput[TResponse]: The parsed output from the language model, conforming to the provided model.
        """
        logger.debug(f"Invoking LLM with pydantic model: {response_model.__name__} for prompt: {prompt} and inputs: {prompt_inputs}")
        output = self.llm.invoke_with_pydantic_model(prompt, prompt_inputs, response_model)
        logger.debug(f"LLM invocation with pydantic model completed with output: {output}")
        return output
