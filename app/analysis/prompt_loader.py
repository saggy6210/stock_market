"""
Prompt Loader.
Handles loading and rendering of prompt templates.
"""

# TODO: Implement prompt loading and rendering:
# - load_prompt(name) - Reads .txt from prompts/ directory
# - render_prompt(name, data) - Safe template rendering (missing keys -> "N/A")


def load_prompt(name: str) -> str:
    """
    Load a prompt template from the prompts directory.
    
    Args:
        name: Name of the prompt file (without extension)
        
    Returns:
        str: The prompt template content
    """
    # TODO: Implement prompt loading
    pass


def render_prompt(name: str, data: dict) -> str:
    """
    Load and render a prompt template with given data.
    
    Args:
        name: Name of the prompt file (without extension)
        data: Dictionary of values to substitute
        
    Returns:
        str: The rendered prompt
    """
    # TODO: Implement safe template rendering
    pass


class SafeFormatDict(dict):
    """Dictionary that returns 'N/A' for missing keys during formatting."""
    
    def __missing__(self, key):
        return "N/A"
