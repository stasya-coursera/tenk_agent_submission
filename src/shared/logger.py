"""Logger utility module using loguru for centralized logging."""

import os
import sys
from typing import Optional
from loguru import logger


def configure_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: Optional[str] = None,
) -> None:
    """
    Configure the global loguru logger with specified settings.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output. If None, only console logging
        rotation: Log file rotation policy (e.g., "10 MB", "1 day")
        retention: How long to keep old log files (e.g., "7 days", "1 month")
        format_string: Custom format string. If None, uses default format
    """
    # Remove default handler
    logger.remove()
    
    # Default format with colors for console
    default_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=log_level,
        format=format_string or default_format,
        colorize=True,
    )
    
    # File handler if specified
    if log_file:
        # Format without colors for file output
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        logger.add(
            log_file,
            level=log_level,
            format=format_string or file_format,
            rotation=rotation,
            retention=retention,
            colorize=False,
        )


def get_logger(name: str) -> "logger":
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)


# Initialize default configuration
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
_log_file = os.getenv("LOG_FILE")

configure_logger(
    log_level=_log_level,
    log_file=_log_file,
)

# Export the main logger for direct use
__all__ = ["logger", "get_logger", "configure_logger"]