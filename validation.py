import streamlit as st
import logging
import traceback
from typing import Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    pass

def validate_credentials(reg_number: str, password: str) -> Tuple[bool, Optional[str]]:
    # Check if credentials are provided
    if not reg_number:
        return False, "Registration number is required"
    
    if not password:
        return False, "Password is required"
    
    # Validate registration number format (assuming it's alphanumeric)
    if not reg_number.strip():
        return False, "Registration number should contain only letters and numbers"
    
    # Validate password length
    if len(password) < 6:
        return False, "Password should be at least 6 characters long"
    
    return True, None

def validate_document_content(content: str) -> Tuple[bool, Optional[str]]:
    """Validate document content
    
    Args:
        content: Document content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if content is empty
    if not content or not content.strip():
        return False, "Document content is empty"
    
    # Check if content is too large (arbitrary limit for demonstration)
    if len(content) > 1000000:  # 1MB of text
        return False, "Document content is too large (max 1MB)"
    
    return True, None

def handle_automation_error(error: Exception) -> Dict[str, Any]:
    """Handle automation errors and provide user-friendly messages
    
    Args:
        error: Exception that occurred
        
    Returns:
        Dict with error details
    """
    error_type = type(error).__name__
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    logger.error(f"Automation error: {error_type}: {error_message}")
    logger.debug(error_traceback)
    
    # Map common errors to user-friendly messages
    user_message = "An error occurred during automation"
    
    if "Timeout" in error_type:
        user_message = "Operation timed out. The website may be slow or unresponsive."
    elif "Navigation" in error_type:
        user_message = "Failed to navigate to the required page. The website structure may have changed."
    elif "Element" in error_type and "not found" in error_message.lower():
        user_message = "Could not find the required element on the page. The website structure may have changed."
    elif "Authentication" in error_message.lower() or "login" in error_message.lower():
        user_message = "Authentication failed. Please check your credentials."
    elif "Network" in error_type:
        user_message = "Network error. Please check your internet connection."
    elif "Permission" in error_type:
        user_message = "Permission denied. The application may not have the required permissions."
    
    return {
        "success": False,
        "error": user_message,
        "error_details": {
            "type": error_type,
            "message": error_message,
            "traceback": error_traceback
        }
    }

def display_error_details(error_result: Dict[str, Any]):
    """Display error details in Streamlit
    
    Args:
        error_result: Error result dictionary
    """
    st.error(error_result.get("error", "An unknown error occurred"))
    
    with st.expander("Error Details", expanded=False):
        if "error_details" in error_result:
            details = error_result["error_details"]
            st.text(f"Error Type: {details.get('type', 'Unknown')}")
            st.text(f"Error Message: {details.get('message', 'No message')}")
            
            if "traceback" in details:
                st.code(details["traceback"], language="python")

def validate_browser_settings(headless: bool, typing_speed: int) -> Tuple[bool, Optional[str]]:
    """Validate browser automation settings
    
    Args:
        headless: Whether to run in headless mode
        typing_speed: Characters per second for typing
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate typing speed
    if typing_speed < 1:
        return False, "Typing speed must be at least 1 character per second"
    
    if typing_speed > 5000:
        return False, "Typing speed cannot exceed 500 characters per second"
    
    return True, None

def validate_chunk_settings(chunk_size: int) -> Tuple[bool, Optional[str]]:
    """Validate document chunking settings
    
    Args:
        chunk_size: Size of document chunks
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate chunk size
    if chunk_size < 100:
        return False, "Chunk size must be at least 100 characters"
    
    if chunk_size > 50000:
        return False, "Chunk size cannot exceed 50,000 characters"
    
    return True, None


def validate_document_content(content):
    """Validate the document content"""
    if not content:
        return False, "Document appears to be empty"
    if len(content) < 10:
        return False, "Document content is too short"
    return True, ""

def validate_browser_settings(headless, typing_speed):
    """Validate the browser automation settings"""
    if typing_speed <= 0:
        return False, "Typing speed must be greater than 0"
    if typing_speed > 1000:
        return False, "Typing speed is unrealistically high"
    return True, ""

def validate_chunk_settings(chunk_size):
    """Validate chunk size settings"""
    if chunk_size <= 0:
        return False, "Chunk size must be greater than 0"
    if chunk_size > 50000:
        return False, "Chunk size is too large, maximum is 50000 characters"
    return True, ""

def handle_automation_error(error):
    """Handle automation errors and create error result object"""
    error_message = str(error)
    logger.error(f"Automation error: {error_message}")
    
    # Map common errors to user-friendly messages
    if "chrome not reachable" in error_message.lower():
        user_message = "Chrome browser is not reachable. Please close all Chrome windows and try again."
    elif "timeout" in error_message.lower():
        user_message = "The operation timed out. VClass might be slow or unresponsive."
    elif "element not interactable" in error_message.lower():
        user_message = "Could not interact with the page elements. VClass interface might have changed."
    elif "invalid credentials" in error_message.lower():
        user_message = "Login failed. Please check your registration number and password."
    else:
        user_message = "An error occurred during automation."
    
    return {
        "success": False,
        "error": user_message,
        "details": error_message,
        "type": "automation_error"
    }

def display_error_details(error_result):
    """Display error details in a user-friendly way"""
    st.error(error_result.get("error", "An unknown error occurred"))
    
    with st.expander("Error Details", expanded=False):
        st.markdown("### Technical Details")
        st.text(error_result.get("details", "No detailed information available"))
        
        if error_result.get("type") == "automation_error":
            st.markdown("### Troubleshooting Tips")
            st.markdown("""
            1. **Close all Chrome windows** and try again
            2. **Check your internet connection** - VClass requires a stable connection
            3. **Verify your credentials** - Make sure your registration number and password are correct
            4. **Try a slower typing speed** - Set typing speed to 20-25 characters per second
            5. **Try smaller chunks** - Set chunk size to 1000-2000 characters
            """)