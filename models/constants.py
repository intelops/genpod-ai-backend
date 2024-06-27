"""
This `enums.py` module contains various enumerations used throughout the project. 
These enumerations provide a systematic way to represent distinct values and 
categories using symbolic names, enhancing the readability and maintainability 
of the code. Each enumeration is defined as a separate class and can be imported 
for use in other modules.
"""

from enum import Enum

class ChatRoles(Enum):
    """
    An enumeration representing the various roles in a chat conversation with 
    the Language Learning Model (LLM) using the ChatPromptTemplate.

    This class is used to categorize the messages in the graph state according 
    to the role of the sender. The roles include 'assistant' (AI), 'tool', 
    'user', and 'system'. These roles help in identifying who sent a particular 
    message or performed a certain action in the conversation.

    Attributes:
        AI (str): Represents the assistant's role in the conversation.
        TOOL (str): Represents the tool's role in the conversation.
        USER (str): Represents the user's role in the conversation.
        SYSTEM (str): Represents the system's role in the conversation.
    """

    AI: str = "assistant"
    TOOL: str = "tool"
    USER: str = "user"
    SYSTEM: str = "system"

    def __str__(self):
        """
        Returns the string representation of the Enum member.

        Returns:
            str: The value of the Enum member.
        """
        return self.value

class Status(Enum):
    """
    An enumeration representing the various states a task or project can be in.

    This class is used to track the progress of a task or project. The states 
    include 'NEW', 'AWAITING', 'INPROGRESS', 'ABANDONED', and 'DONE'. These 
    states help in identifying the current status of a task or project.

    Attributes:
        NEW (str): Represents the initial state of a task or project.
        AWAITING (str): Represents the state when a task or project is waiting
          for some event or dependency.
        INPROGRESS (str): Represents the state when a task or project is 
          currently being worked on.
        ABANDONED (str): Represents the state when a task or project has been 
          left incomplete.
        DONE (str): Represents the state when a task or project has been 
          completed.
    """
    NEW: str = "NEW"
    AWAITING: str = "AWAITING"
    INPROGRESS: str = "INPROGRESS"
    ABANDONED: str = "ABANDONED"
    DONE: str = "DONE"

    def __str__(self):
        """
        Returns the string representation of the Enum member.

        Returns:
            str: The value of the Enum member.
        """
        return self.value


class PStatus(Enum):
    """
    An enumeration representing the various states a project can be in.

    This class is used to track the progress of a project. The states
    include 'NEW', 'INITIAL', 'EXECUTING', 'MONITORING', and 'HALTED'. These
    states help in identifying the current status of a task or project.

    Attributes:
        NEW (str): Represents the Pre-init state of a project.
        INITIAL (str): Represents the inital state when a project is waiting
          for the setup to be completed.
        EXECUTING (str): Represents the state of the project when a task is
          currently being worked on.
        MONITORING (str): Represents the state of the project when an issue as
          arised while executing a task.
        HALTED (str): Represents the final state of the project when all tasks
          have been completed or something could not be resolved so, use this to loop in HUMAN.
    """
    NEW: str = "NEW"
    INITIAL: str = "INITIAL"
    EXECUTING: str = "EXECUTING"
    MONITORING: str = "MONITORING"
    HALTED: str = "HALTED"

    def __str__(self):
        """
        Returns the string representation of the Enum member.

        Returns:
            str: The value of the Enum member.
        """
        return self.value
