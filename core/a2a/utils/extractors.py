"""
Utilities for extracting data from A2A messages.

Implements Strategy pattern for different extraction methods.
"""

from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from a2a.types import Message, DataPart
from core.a2a.exceptions import A2AInputExtractionError
from utils.logger import logger

T = TypeVar('T', bound=BaseModel)


class MessageExtractor:
    """
    Utility class for extracting data from A2A messages.
    
    This class provides reusable methods for extracting agent inputs
    from A2A protocol messages.
    """
    
    @staticmethod
    def extract_agent_input(
        message: Optional[Message],
        input_model: Type[T],
        field_name: str = "agent_input"
    ) -> T:
        """
        Extract and validate agent input from A2A message.
        
        This method looks for a DataPart in the message containing
        the specified field name and validates it against the input model.
        
        Args:
            message: The A2A message to extract from
            input_model: Pydantic model class for validation
            field_name: Name of the field containing agent input
            
        Returns:
            Validated instance of input_model
            
        Raises:
            A2AInputExtractionError: If extraction or validation fails
        """
        if not message:
            raise A2AInputExtractionError("Message is required")
        
        if not message.parts:
            raise A2AInputExtractionError("Message has no parts")
        
        # Look for agent input in message parts
        for part in message.parts:
            # Handle Part wrapper
            if hasattr(part, 'root'):
                part = part.root
            
            if isinstance(part, DataPart) and field_name in part.data:
                try:
                    # Extract and validate input
                    input_data = part.data[field_name]
                    return input_model(**input_data)
                except Exception as e:
                    logger.error(f"Failed to parse {field_name}: {e}")
                    raise A2AInputExtractionError(
                        f"Invalid {field_name}: {str(e)}"
                    )
        
        raise A2AInputExtractionError(
            f"No {field_name} found in message parts. "
            f"Expected a DataPart with '{field_name}' field."
        )
    
    @staticmethod
    def extract_raw_data(
        message: Optional[Message],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Extract raw data from message without validation.
        
        Args:
            message: The A2A message to extract from
            field_name: Name of the field to extract
            
        Returns:
            Raw data dictionary
            
        Raises:
            A2AInputExtractionError: If extraction fails
        """
        if not message:
            raise A2AInputExtractionError("Message is required")
        
        for part in message.parts:
            if hasattr(part, 'root'):
                part = part.root
                
            if isinstance(part, DataPart) and field_name in part.data:
                return part.data[field_name]
        
        raise A2AInputExtractionError(f"Field '{field_name}' not found in message")
    
    @staticmethod
    def has_field(message: Optional[Message], field_name: str) -> bool:
        """
        Check if a field exists in the message.
        
        Args:
            message: The A2A message to check
            field_name: Name of the field to look for
            
        Returns:
            True if field exists, False otherwise
        """
        if not message or not message.parts:
            return False
        
        for part in message.parts:
            if hasattr(part, 'root'):
                part = part.root
                
            if isinstance(part, DataPart) and field_name in part.data:
                return True
        
        return False