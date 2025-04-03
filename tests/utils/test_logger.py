"""
Test Suite for Logger Utilities Module

This module provides extensive unit tests for the freeipaconsistencycheck
logging configuration and setup utilities. It validates the robustness
of logger initialization, configuration, and handling of various
logging scenarios.

Key Testing Objectives:
- Validate logger configuration mechanisms
- Test logging level and handler setup
- Verify debug, verbose, and quiet mode behaviors
- Ensure robust file logging capabilities
- Check error handling in logging configuration

Test Coverage:
- Basic logger configuration
- Debug mode logging
- Verbose mode logging
- Quiet mode logging
- File logging setup
- Error handling in file logging
- Handler management
"""

import pytest
import logging
from unittest.mock import patch, MagicMock

from freeipaconsistencycheck.utils.logger import setup_logger


@pytest.fixture
def mock_logger_with_handlers():
    """Create a mock logger with the handlers attribute properly set up."""
    logger = MagicMock(spec=logging.Logger)
    # This is the key fix - setting handlers as an empty list
    logger.handlers = []
    return logger


class TestSetupLogger:
    """Tests for the setup_logger function."""

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    def test_basic_configuration(
        self, mock_file_handler, mock_stream_handler, mock_get_logger
    ):
        """Test basic logger configuration."""
        # Create a properly configured mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Key fix - add handlers attribute
        mock_get_logger.return_value = mock_logger

        mock_console_handler = MagicMock()
        mock_stream_handler.return_value = mock_console_handler

        # Create a simple args object
        args = MagicMock()
        args.debug = False
        args.verbose = False
        args.quiet = False
        args.log_file = None

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify the logger was configured correctly
        assert logger == mock_logger
        mock_get_logger.assert_called_with("testapp")
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

        # Verify a console handler was added
        mock_stream_handler.assert_called_once()
        mock_logger.addHandler.assert_called_with(mock_console_handler)

        # Verify no file handler was added
        mock_file_handler.assert_not_called()

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    def test_debug_mode(self, mock_file_handler, mock_stream_handler, mock_get_logger):
        """Test logger configuration in debug mode."""
        # Create mock objects
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Key fix - add handlers attribute
        mock_get_logger.return_value = mock_logger

        mock_console_handler = MagicMock()
        mock_stream_handler.return_value = mock_console_handler

        # Create a simple args object with debug enabled
        args = MagicMock()
        args.debug = True
        args.verbose = False
        args.quiet = False
        args.log_file = None

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify the console handler was set to DEBUG level
        mock_console_handler.setLevel.assert_called_once_with(logging.DEBUG)

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    def test_verbose_mode(
        self, mock_file_handler, mock_stream_handler, mock_get_logger
    ):
        """Test logger configuration in verbose mode."""
        # Create mock objects
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Key fix - add handlers attribute
        mock_get_logger.return_value = mock_logger

        mock_console_handler = MagicMock()
        mock_stream_handler.return_value = mock_console_handler

        # Create a simple args object with verbose enabled
        args = MagicMock()
        args.debug = False
        args.verbose = True
        args.quiet = False
        args.log_file = None

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify the console handler was set to INFO level
        mock_console_handler.setLevel.assert_called_once_with(logging.INFO)

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    def test_quiet_mode(self, mock_file_handler, mock_stream_handler, mock_get_logger):
        """Test logger configuration in quiet mode."""
        # Create mock objects
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Key fix - add handlers attribute
        mock_get_logger.return_value = mock_logger

        # Create a simple args object with quiet enabled
        args = MagicMock()
        args.debug = False
        args.verbose = False
        args.quiet = True
        args.log_file = None

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify no console handler was added
        mock_stream_handler.assert_not_called()

        # Verify no file handler was added
        mock_file_handler.assert_not_called()

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    @patch("os.path.dirname")
    @patch("os.makedirs")
    def test_file_logging(
        self,
        mock_makedirs,
        mock_dirname,
        mock_file_handler,
        mock_stream_handler,
        mock_get_logger,
    ):
        """Test logger configuration with file logging."""
        # Create mock objects
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Add handlers attribute
        mock_get_logger.return_value = mock_logger

        mock_console_handler = MagicMock()
        mock_stream_handler.return_value = mock_console_handler

        mock_file_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_file_handler_instance

        # Create a simple args object with file logging
        args = MagicMock()
        args.debug = False
        args.verbose = False
        args.quiet = False
        args.log_file = "/path/to/log/file.log"

        # Setup dirname mocking
        mock_dirname.return_value = "/path/to/log"

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify that directory creation was attempted
        mock_makedirs.assert_called_once_with("/path/to/log", exist_ok=True)

        # Verify file handler was created and added
        mock_file_handler.assert_called_once_with("/path/to/log/file.log")
        assert mock_logger.addHandler.called

    @patch("logging.getLogger")
    @patch("logging.StreamHandler")
    @patch("logging.FileHandler")
    def test_file_logging_error(
        self, mock_file_handler, mock_stream_handler, mock_get_logger
    ):
        """Test error handling for file logging."""
        # Create mock objects
        mock_logger = MagicMock(spec=logging.Logger)
        mock_logger.handlers = []  # Key fix - add handlers attribute
        mock_get_logger.return_value = mock_logger

        mock_console_handler = MagicMock()
        mock_stream_handler.return_value = mock_console_handler

        # Make file handler raise an error
        mock_file_handler.side_effect = IOError("Permission denied")

        # Create a simple args object with file logging
        args = MagicMock()
        args.debug = False
        args.verbose = False
        args.quiet = False
        args.log_file = "/path/to/log/file.log"

        # Call the function
        logger = setup_logger(app_name="testapp", args=args)

        # Verify error handling - an error should be logged
        assert mock_logger.error.called
