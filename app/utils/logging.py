"""
Logging Configuration.
Sets up Python logging with consistent formatting.
"""

# TODO: Implement configure_logging() function with:
# - Format: timestamp | level | logger | message
# - Log level configurable via settings (default INFO)

import logging


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # TODO: Implement logging configuration
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
