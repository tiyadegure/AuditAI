"""
Logger utility

All logging is routed to **stderr**. This is critical for the MCP stdio
transport: stdout is reserved exclusively for JSON-RPC protocol messages,
and any log line written to stdout corrupts the stream (the client fails to
parse it as JSON-RPC). Rich's RichHandler defaults to stdout, so we pass it a
Console bound to stderr.
"""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler

# Single stderr-bound console shared by all loggers.
_STDERR_CONSOLE = Console(stderr=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with rich formatting that writes to stderr.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = RichHandler(
            console=_STDERR_CONSOLE,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Don't propagate to the root logger (which may have a stdout handler).
        logger.propagate = False
    
    return logger
