"""
Logging configuration for the freeipaconsistencycheck package.

This module provides a unified logging setup for the application using Python's
standard logging library, supporting different verbosity levels, console and file
outputs, and customizable formatting.
"""

import logging
import os
import sys
from typing import Any


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context information to log messages.

    This adapter prepends context data to log messages to provide additional
    relevant information without changing the logging API.
    """

    def process(self, msg, kwargs):
        """
        Process the log message to add context information.

        Args:
            msg: Original log message
            kwargs: Logging keyword arguments

        Returns:
            Tuple of (modified message, kwargs)
        """
        context_string = " ".join(
            f"[{key}={value}]" for key, value in self.extra.items()
        )
        return f"{context_string} {msg}", kwargs


def setup_logger(
    app_name: str, args: Any, default_level: str = "WARNING"
) -> logging.Logger:
    """
    Set up and configure a logger with consistent formatting and handlers.

    Args:
        app_name: Application name for logger identification
        args: Command line arguments containing logging options
        default_level: Default log level if not specified in args

    Returns:
        Configured logger instance ready for use
    """
    # Check if necessary attributes exist on args
    has_debug = hasattr(args, "debug") and args.debug
    has_verbose = hasattr(args, "verbose") and args.verbose
    has_quiet = hasattr(args, "quiet") and args.quiet
    has_log_file = hasattr(args, "log_file") and args.log_file

    # Get or create logger
    logger = logging.getLogger(app_name)

    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set the base log level
    logger.setLevel(logging.DEBUG)

    # Determine console log level based on flags
    if has_debug:
        console_level = logging.DEBUG
    elif has_verbose:
        console_level = logging.INFO
    else:
        console_level = getattr(logging, default_level)

    # Create console handler unless quiet mode is enabled
    if not has_quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)

        # Create formatter with timestamp
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if has_log_file:
        try:
            # Convert to string path if needed
            log_path = str(args.log_file)

            # Ensure log directory exists
            log_dir = os.path.dirname(log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            # Create file handler using string path
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)  # Always use DEBUG for file

            # Create formatter with more details for file logging
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # Don't crash if file logging setup fails
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.ERROR)
            logger.addHandler(stderr_handler)
            logger.error(f"Failed to set up log file {args.log_file}: {e}")
    return logger


def get_console_logger(
    log_level: str = "WARNING", app_name: str = "freeipaconsistencycheck"
) -> logging.Logger:
    """
    Create a simple console logger with the specified log level.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        app_name: Application name for logger identification

    Returns:
        Configured logger instance with console handler
    """

    class Args:
        def __init__(self, level):
            self.debug = level == "DEBUG"
            self.verbose = level == "INFO"
            self.quiet = False
            self.log_file = None

    args = Args(log_level)
    return setup_logger(app_name=app_name, args=args)


def get_null_logger() -> logging.Logger:
    """
    Create a null logger that doesn't output anything.

    This is useful for disabling logging without changing code.

    Returns:
        Logger instance that discards all log messages
    """
    logger = logging.getLogger("null")
    logger.setLevel(logging.CRITICAL + 1)  # Above the highest standard level
    logger.addHandler(logging.NullHandler())
    return logger
