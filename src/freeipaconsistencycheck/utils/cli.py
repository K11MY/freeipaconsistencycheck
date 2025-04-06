"""
Command Line Interface handling for the freeipaconsistencycheck package.

This module provides functions to parse and handle command line arguments,
including validation, help messages, and default values. It uses argparse for
robust command-line argument parsing and organizes options into logical groups
for better usability.

The module offers both functional and object-oriented interfaces for argument
handling, with the CommandLineArgs class providing a structured container for
all parsed arguments.
"""

import argparse
from typing import Optional, List, NamedTuple, Any


class CommandLineArgs(NamedTuple):
    """
    Structured container for parsed command line arguments.

    This immutable class provides a strongly-typed, named-field container
    for all command line arguments, making it easier to access and validate
    argument values throughout the application.

    Attributes:
        hosts: List of IPA server hostnames, or None if not specified
        domain: IPA domain name, or None if not specified
        binddn: Distinguished name for LDAP binding, or None if not specified
        bindpw: Password for LDAP binding, or None if not specified
        debug: Flag to enable debugging mode
        verbose: Flag to enable verbose output
        quiet: Flag to disable console output
        log_file: Path to log file, or None for no logging to file
        disable_header: Flag to disable table header in output
        disable_border: Flag to disable table border in output
        output_format: Output format for structured data (json/yaml), or None for standard output
    """

    hosts: Optional[List[str]]
    domain: Optional[str]
    binddn: Optional[str]
    bindpw: Optional[str]
    debug: bool
    verbose: bool
    quiet: bool
    log_file: Optional[str]
    disable_header: bool
    disable_border: bool
    output_format: Optional[str]


def create_parser(app_name: str, version: str) -> argparse.ArgumentParser:
    """
    Create and configure the argument parser with all supported options.

    Creates an ArgumentParser instance with option groups for connection settings,
    general options, logging configuration, output formatting, and structured output.
    The parser is configured with the application name and version.

    Args:
        app_name: The name of the application (used in help text)
        version: The application version string (used in version display)

    Returns:
        A fully configured ArgumentParser instance ready to parse command-line arguments

    Notes:
        - Options are organized into logical groups for better help text readability
        - Each option includes a help message explaining its purpose
        - Default values are shown in help text where applicable
        - The --help option is handled manually to allow for customized help display
    """
    parser = argparse.ArgumentParser(
        description="Tool to check consistency across FreeIPA servers", add_help=False
    )

    # Connection options
    connection_group = parser.add_argument_group("Connection Options")
    connection_group.add_argument(
        "-H",
        "--hosts",
        nargs="*",
        dest="hosts",
        help="list of IPA servers to check for consistency",
    )
    connection_group.add_argument(
        "-d", "--domain", nargs="?", dest="domain", help="IPA domain name"
    )
    connection_group.add_argument(
        "-D",
        "--binddn",
        nargs="?",
        dest="binddn",
        help="Bind DN (default: cn=Directory Manager)",
    )
    connection_group.add_argument(
        "-W",
        "--bindpw",
        nargs="?",
        dest="bindpw",
        help="Bind password for LDAP authentication",
    )

    # General options
    general_group = parser.add_argument_group("General Options")
    general_group.add_argument(
        "--help", action="help", help="show this help message and exit"
    )
    general_group.add_argument(
        "--version",
        action="version",
        version=f"{app_name} {version}",
        help="show program version and exit",
    )

    # Logging options
    logging_group = parser.add_argument_group("Logging Options")
    logging_group.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        help="enable debugging mode with detailed log output",
    )
    logging_group.add_argument(
        "--verbose",
        action="store_true",
        dest="verbose",
        help="enable verbose mode with additional information",
    )
    logging_group.add_argument(
        "--quiet",
        action="store_true",
        dest="quiet",
        help="suppress all output to console (useful for scripting)",
    )
    logging_group.add_argument(
        "-l",
        "--log-file",
        nargs="?",
        dest="log_file",
        default="not_set",
        help=f"log to file (./{app_name}.log by default)",
    )

    # Output formatting options
    format_group = parser.add_argument_group("Output Formatting")
    format_group.add_argument(
        "--no-header",
        action="store_true",
        dest="disable_header",
        help="disable table header in the output display",
    )
    format_group.add_argument(
        "--no-border",
        action="store_true",
        dest="disable_border",
        help="disable table border in the output display",
    )

    # Structured output options
    output_group = parser.add_argument_group("Structured Output")
    output_group.add_argument(
        "-o",
        "--output",
        nargs="?",
        dest="output_format",
        choices=["json", "yaml"],
        help="Output format for structured data (json or yaml)",
        default="not_set",
    )

    return parser


def process_args(args: argparse.Namespace, app_name: str) -> CommandLineArgs:
    """
    Process parsed arguments to handle defaults and special cases.

    Takes the raw parsed arguments from argparse and performs additional processing
    to resolve default values, handle special cases, and convert them into a
    strongly-typed CommandLineArgs container.

    Args:
        args: Raw parsed arguments from argparse
        app_name: The name of the application (used for default log filename)

    Returns:
        A CommandLineArgs instance containing the processed arguments
    """
    # Handle log file argument
    if not hasattr(args, "log_file") or args.log_file == "not_set":
        log_file = None
    elif args.log_file == "":
        log_file = f"{app_name}.log"
    else:
        log_file = args.log_file

    # Handle output format argument
    if not hasattr(args, "output_format") or args.output_format == "not_set":
        output_format = None
    else:
        output_format = args.output_format

    # Create a CommandLineArgs instance with processed values
    return CommandLineArgs(
        hosts=args.hosts if hasattr(args, "hosts") else None,
        domain=args.domain if hasattr(args, "domain") else None,
        binddn=args.binddn if hasattr(args, "binddn") else None,
        bindpw=args.bindpw if hasattr(args, "bindpw") else None,
        debug=args.debug if hasattr(args, "debug") else False,
        verbose=args.verbose if hasattr(args, "verbose") else False,
        quiet=args.quiet if hasattr(args, "quiet") else False,
        log_file=log_file,
        disable_header=(
            args.disable_header if hasattr(args, "disable_header") else False
        ),
        disable_border=(
            args.disable_border if hasattr(args, "disable_border") else False
        ),
        output_format=output_format,
    )


def parse_arguments(app_name: str, version: str) -> CommandLineArgs:
    """
    Parse command line arguments and return processed results.

    This is the main entry point for command-line argument handling. It creates
    an argument parser, processes the command line arguments, and returns a
    structured object with the parsed and validated values.

    Args:
        app_name: The name of the application
        version: The application version string

    Returns:
        A CommandLineArgs object containing the processed arguments

    Example:
        ```python
        # In your main application code
        from freeipaconsistencycheck.utils.cli import parse_arguments

        args = parse_arguments("cipa", "1.0.0")
        if args.verbose:
            print(f"Checking servers: {', '.join(args.hosts)}")
        ```
    """
    parser = create_parser(app_name, version)
    raw_args = parser.parse_args()
    return process_args(raw_args, app_name)


def get_help_text(app_name: str, version: str) -> str:
    """
    Get the help text for the application without running the parser.

    This function is useful for generating documentation or displaying help
    without executing the full application or parsing actual command-line arguments.

    Args:
        app_name: The name of the application
        version: The application version string

    Returns:
        The formatted help text as a string

    Example:
        ```python
        # Generate help text for inclusion in documentation
        help_text = get_help_text("cipa", "1.0.0")
        with open("docs/cli_help.txt", "w") as f:
            f.write(help_text)
        ```
    """
    parser = create_parser(app_name, version)
    return parser.format_help()


def validate_cli_args(args: CommandLineArgs) -> List[str]:
    """
    Validate command line arguments for logical consistency and correctness.

    Performs additional validation beyond what argparse can do, checking for
    logical errors, inconsistencies between parameters, and other constraints.

    Args:
        args: The processed command line arguments

    Returns:
        A list of error messages (empty if no errors)

    Example:
        ```python
        args = parse_arguments(app_name, version)
        errors = validate_cli_args(args)
        if errors:
            for error in errors:
                print(f"Error: {error}")
            sys.exit(1)
        ```
    """
    errors = []

    # Check for incompatible options
    if args.quiet and args.verbose:
        errors.append("Cannot use both --quiet and --verbose options simultaneously")

    return errors
