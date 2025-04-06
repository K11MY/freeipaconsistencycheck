"""
Tests for the command-line interface module.

This module provides comprehensive unit tests for the freeipaconsistencycheck
command-line interface (CLI) module. It verifies the correct functionality
of argument parsing, processing, and validation mechanisms.

Key Testing Objectives:
- Validate parser creation and configuration
- Test argument processing logic
- Verify argument validation mechanisms
- Ensure robust error handling for CLI arguments

Test Coverage:
- Parser option verification
- Log file processing scenarios
- Output format configuration handling
- Argument validation for various edge cases
- Help text generation
"""

import sys
from unittest.mock import patch

from freeipaconsistencycheck.utils.cli import (
    parse_arguments,
    CommandLineArgs,
    create_parser,
    process_args,
    get_help_text,
    validate_cli_args,
)


class TestCreateParser:
    """Tests for the create_parser function."""

    def test_parser_creation(self):
        """Test that the parser is created with the correct options."""
        parser = create_parser("cipa", "1.0.0")

        # Verify the parser has the expected description
        assert "consistency across FreeIPA servers" in parser.description

        # Get all option strings from the parser
        options = []
        for action in parser._actions:
            options.extend(action.option_strings)

        # Verify that essential options are present
        assert "--hosts" in options
        assert "--domain" in options
        assert "--binddn" in options
        assert "--bindpw" in options
        assert "--debug" in options
        assert "--verbose" in options
        assert "--quiet" in options
        assert "--log-file" in options
        assert "--no-header" in options
        assert "--no-border" in options
        assert "--output" in options  # New option for structured output


class TestProcessArgs:
    """Tests for the process_args function."""

    def test_default_log_file(self):
        """Test handling of default log file setting."""

        # Create a minimal args object
        class Args:
            log_file = None
            output_format = None
            debug = False
            verbose = False
            quiet = False
            disable_header = False
            disable_border = False
            domain = None
            hosts = None
            binddn = None
            bindpw = None

        args = Args()
        result = process_args(args, "testapp")

        # Verify that log_file is None (disabled)
        assert result.log_file is None

        # Now test with an empty string (use default filename)
        args.log_file = ""
        result = process_args(args, "testapp")

        # Verify that the default log file name is used
        assert result.log_file == "testapp.log"

        # Test with 'not_set'
        args.log_file = "not_set"
        result = process_args(args, "testapp")

        # Verify that log_file is None
        assert result.log_file is None

        # Test with a specific filename
        args.log_file = "custom.log"
        result = process_args(args, "testapp")

        # Verify that the custom filename is used
        assert result.log_file == "custom.log"

    def test_output_format_processing(self):
        """Test handling of output_format setting."""

        # Create a minimal args object
        class Args:
            log_file = None
            output_format = None
            debug = False
            verbose = False
            quiet = False
            disable_header = False
            disable_border = False
            domain = None
            hosts = None
            binddn = None
            bindpw = None

        args = Args()

        # Test with None
        args.output_format = None
        result = process_args(args, "testapp")
        assert result.output_format is None

        # Test with 'not_set'
        args.output_format = "not_set"
        result = process_args(args, "testapp")
        assert result.output_format is None

        # Test with 'json'
        args.output_format = "json"
        result = process_args(args, "testapp")
        assert result.output_format == "json"

        # Test with 'yaml'
        args.output_format = "yaml"
        result = process_args(args, "testapp")
        assert result.output_format == "yaml"

    def test_return_type(self):
        """Test that the return value is a CommandLineArgs instance."""

        # Create a minimal args object
        class Args:
            log_file = None
            output_format = None
            debug = False
            verbose = False
            quiet = False
            disable_header = False
            disable_border = False
            domain = None
            hosts = None
            binddn = None
            bindpw = None

        args = Args()
        result = process_args(args, "testapp")

        # Verify that the result is a CommandLineArgs instance
        assert isinstance(result, CommandLineArgs)

        # Verify that all attributes are present
        assert hasattr(result, "log_file")
        assert hasattr(result, "output_format")
        assert hasattr(result, "debug")
        assert hasattr(result, "verbose")
        assert hasattr(result, "quiet")
        assert hasattr(result, "disable_header")
        assert hasattr(result, "disable_border")
        assert hasattr(result, "domain")
        assert hasattr(result, "hosts")
        assert hasattr(result, "binddn")
        assert hasattr(result, "bindpw")


class TestParseArguments:
    """Tests for the parse_arguments function."""

    def test_parse_arguments(self):
        """Test the full argument parsing process."""
        # Mock sys.argv
        test_args = [
            "cipa",  # Program name
            "--domain",
            "example.com",
            "--hosts",
            "server1.example.com",
            "server2.example.com",
            "--binddn",
            "cn=Directory Manager",
            "--bindpw",
            "secret",
            "--verbose",
            "--no-header",
            "--output",
            "json",
        ]

        with patch.object(sys, "argv", test_args):
            # Create a minimal parser that doesn't need all the options
            with patch(
                "freeipaconsistencycheck.utils.cli.create_parser"
            ) as mock_create_parser:
                with patch(
                    "freeipaconsistencycheck.utils.cli.process_args"
                ) as mock_process_args:
                    # Mock the parser and its parse_args method
                    mock_parser = mock_create_parser.return_value
                    mock_parser.parse_args.return_value = "raw_args"

                    # Mock process_args to return a known value
                    expected_result = CommandLineArgs(
                        domain="example.com",
                        hosts=["server1.example.com", "server2.example.com"],
                        binddn="cn=Directory Manager",
                        bindpw="secret",
                        debug=False,
                        verbose=True,
                        quiet=False,
                        log_file=None,
                        disable_header=True,
                        disable_border=False,
                        output_format="json",
                    )
                    mock_process_args.return_value = expected_result

                    # Call the function
                    result = parse_arguments("cipa", "1.0.0")

                    # Verify the result
                    assert result == expected_result

                    # Verify the mocked functions were called with the expected arguments
                    mock_create_parser.assert_called_once_with("cipa", "1.0.0")
                    mock_parser.parse_args.assert_called_once()
                    mock_process_args.assert_called_once_with("raw_args", "cipa")


class TestGetHelpText:
    """Tests for the get_help_text function."""

    def test_get_help_text(self):
        """Test retrieving help text."""
        with patch(
            "freeipaconsistencycheck.utils.cli.create_parser"
        ) as mock_create_parser:
            # Mock the parser and its format_help method
            mock_parser = mock_create_parser.return_value
            mock_parser.format_help.return_value = "Sample help text"

            # Call the function
            result = get_help_text("cipa", "1.0.0")

            # Verify the result
            assert result == "Sample help text"

            # Verify the mocked functions were called with the expected arguments
            mock_create_parser.assert_called_once_with("cipa", "1.0.0")
            mock_parser.format_help.assert_called_once()


class TestValidateCliArgs:
    """Tests for the validate_cli_args function."""

    def test_valid_args(self):
        """Test validation with valid arguments."""
        args = CommandLineArgs(
            domain="example.com",
            hosts=["server1.example.com", "server2.example.com"],
            binddn="cn=Directory Manager",
            bindpw="secret",
            debug=False,
            verbose=False,
            quiet=False,
            log_file=None,
            disable_header=False,
            disable_border=False,
            output_format="json",
        )

        # Validation should pass (return empty list)
        errors = validate_cli_args(args)
        assert errors == []

    def test_incompatible_options(self):
        """Test validation with incompatible options."""
        args = CommandLineArgs(
            domain="example.com",
            hosts=["server1.example.com", "server2.example.com"],
            binddn="cn=Directory Manager",
            bindpw="secret",
            debug=False,
            verbose=True,  # Verbose and quiet both enabled
            quiet=True,
            log_file=None,
            disable_header=False,
            disable_border=False,
            output_format="json",
        )

        # Validation should fail
        errors = validate_cli_args(args)
        assert len(errors) == 1
        assert "quiet" in errors[0].lower()
        assert "verbose" in errors[0].lower()

    def test_multiple_output_formats(self):
        """Test with different output formats."""
        # Test with JSON format
        args = CommandLineArgs(
            domain="example.com",
            hosts=["server1.example.com"],
            binddn="cn=Directory Manager",
            bindpw="secret",
            debug=False,
            verbose=False,
            quiet=False,
            log_file=None,
            disable_header=False,
            disable_border=False,
            output_format="json",
        )
        errors = validate_cli_args(args)
        assert errors == []

        # Test with YAML format
        args = CommandLineArgs(
            domain="example.com",
            hosts=["server1.example.com"],
            binddn="cn=Directory Manager",
            bindpw="secret",
            debug=False,
            verbose=False,
            quiet=False,
            log_file=None,
            disable_header=False,
            disable_border=False,
            output_format="yaml",
        )
        errors = validate_cli_args(args)
        assert errors == []

        # Test with no output format
        args = CommandLineArgs(
            domain="example.com",
            hosts=["server1.example.com"],
            binddn="cn=Directory Manager",
            bindpw="secret",
            debug=False,
            verbose=False,
            quiet=False,
            log_file=None,
            disable_header=False,
            disable_border=False,
            output_format=None,
        )
        errors = validate_cli_args(args)
        assert errors == []
