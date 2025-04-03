#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tool to check consistency across FreeIPA servers.

This module provides the main entry point and core functionality for the
freeipaconsistencycheck tool. It handles initialization, command-line processing,
server connection, consistency checking, and results display.

The architecture follows a clean separation of concerns:
- Application: Handles initialization and orchestration
- ConsistencyChecker: Performs the actual consistency checks
- Utility modules: Provide supporting functionality

This design allows for easier testing, maintenance, and extension of the
functionality while keeping the core logic clear and focused.
"""

import os
import sys
import json
import yaml
import logging
from collections import OrderedDict
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from freeipaconsistencycheck.utils.loading_indicator import LoadingIndicator

# For table display
from prettytable import PrettyTable

# Internal imports
from .__version__ import __version__
from .server import FreeIPAServer

# Utility imports - use consistent import approach (relative or absolute)
# Here using absolute imports for clarity since these are well-established modules
from freeipaconsistencycheck.utils.cli import parse_arguments, CommandLineArgs
from freeipaconsistencycheck.utils.config import Config, ConfigError
from freeipaconsistencycheck.utils.logger import setup_logger
from freeipaconsistencycheck.utils.dns_utils import find_ipa_servers


class ConsistencyChecker:
    """
    Check consistency across FreeIPA servers and display results.

    This class encapsulates the logic for comparing configuration and state
    data across multiple FreeIPA servers, determining consistency, and
    presenting the results in various formats.

    Attributes:
        servers (Dict[str, FreeIPAServer]): Dictionary mapping server hostnames to server objects
        args (CommandLineArgs): Processed command-line arguments
        checks (OrderedDict): Dictionary mapping check names to display names
    """

    def __init__(self, servers: Dict[str, FreeIPAServer], args: CommandLineArgs):
        """
        Initialize the consistency checker.

        Args:
            servers: Dictionary mapping server names to FreeIPAServer instances
            args: Processed command line arguments

        Raises:
            ValueError: If servers dictionary is empty
        """
        if not servers:
            raise ValueError("No servers provided for consistency checking")

        self.servers = servers
        self.args = args

        # Define the checks to perform and their display names
        self.checks = OrderedDict(
            [
                ("users", "Active Users"),
                ("susers", "Stage Users"),
                ("pusers", "Preserved Users"),
                ("hosts", "Hosts"),
                ("services", "Services"),
                ("ugroups", "User Groups"),
                ("hgroups", "Host Groups"),
                ("ngroups", "Netgroups"),
                ("hbac", "HBAC Rules"),
                ("sudo", "SUDO Rules"),
                ("zones", "DNS Zones"),
                ("certs", "Certificates"),
                ("conflicts", "LDAP Conflicts"),
                ("ghosts", "Ghost Replicas"),
                ("bind", "Anonymous BIND"),
                ("msdcs", "Microsoft ADTrust"),
                ("replicas", "Replication Status"),
            ]
        )

    def is_consistent(self, check: str, check_results: List[Any]) -> bool:
        """
        Determine if a specific check is consistent across all servers.

        A check is consistent if either:
        1. All servers report the same value (for most checks)
        2. For certain checks (conflicts, ghosts, replicas), special rules apply

        Args:
            check: The name of the check to evaluate
            check_results: List of check results from all servers

        Returns:
            True if results are consistent, False otherwise

        Notes:
            - For 'conflicts' and 'ghosts', consistent means all servers report 0
            - For 'replicas', consistent means all servers report healthy agreements
            - For other checks, consistent means all servers report the same non-None value
        """
        # Empty results are never consistent
        if not check_results:
            return False

        # Special case: LDAP conflicts - all must be 0
        if check == "conflicts":
            conflicts = [
                getattr(server, "conflicts") for server in self.servers.values()
            ]
            return conflicts.count(conflicts[0]) == len(conflicts) and conflicts[0] == 0

        # Special case: Ghost replicas - all must be 0
        elif check == "ghosts":
            ghosts = [getattr(server, "ghosts") for server in self.servers.values()]
            return ghosts.count(ghosts[0]) == len(ghosts) and ghosts[0] == 0

        # Special case: Replication agreements - all must be healthy
        elif check == "replicas":
            healths = [
                getattr(server, "healthy_agreements")
                for server in self.servers.values()
            ]
            return healths.count(healths[0]) == len(healths) and healths[0]

        # Default case: All values must be identical and none can be None
        return (
            check_results.count(check_results[0]) == len(check_results)
            and None not in check_results
        )

    def print_table(self, log: logging.Logger) -> None:
        """
        Print a formatted table of check results across all servers.

        Creates a table with rows for each check and columns for each server,
        plus a final column showing the consistency state.

        Args:
            log: Logger instance for output

        Notes:
            - Uses PrettyTable for formatting
            - Respects the disable_header and disable_border settings
            - Logs the table at INFO level and also prints directly to stdout
            when not in debug mode
        """
        # Create column headers with server hostnames
        headers = (
            ["FreeIPA servers:"]
            + [getattr(server, "hostname_short") for server in self.servers.values()]
            + ["STATE"]
        )

        # Create the table
        table = PrettyTable(
            headers,
            header=not self.args.disable_header,
            border=not self.args.disable_border,
        )
        table.align = "l"  # Left-align all columns

        # Add rows for each check
        for check_name, display_name in self.checks.items():
            # Get values for this check across all servers
            check_results = [
                getattr(server, check_name) for server in self.servers.values()
            ]

            # Determine if this check is consistent
            state = "OK" if self.is_consistent(check_name, check_results) else "FAIL"

            # Add the row to the table
            table.add_row(
                [display_name]  # Check name
                + check_results  # Values from each server
                + [state]  # Consistency state
            )

        # Log the table at INFO level for log files
        log.info("\nConsistency check results:\n%s", table)

        # Only print directly to stdout if not in debug mode (to avoid duplication)
        # and not in quiet mode
        if not self.args.debug and not self.args.quiet:
            print("\nConsistency check results:\n" + table.get_string())

    def get_structured_data(self) -> Dict[str, Any]:
        """
        Generate structured data of consistency check results.

        Creates a structured data format suitable for conversion to JSON or YAML,
        containing all consistency check results and server information.

        Returns:
            A dictionary containing structured consistency check data
        """
        # Create a structure to hold all the data
        structured_data: Dict[str, Any] = {
            "timestamp": None,  # Will be filled by the caller with current time
            "domain": None,  # Will be filled by the caller
            "servers": [],
            "checks": [],
            "summary": {
                "total_checks": len(self.checks),
                "consistent_checks": 0,
                "inconsistent_checks": 0,
            },
        }

        # Add server information
        for hostname, server in self.servers.items():
            server_info = {
                "hostname": hostname,
                "hostname_short": getattr(server, "hostname_short"),
            }
            structured_data["servers"].append(server_info)

        # Add check results
        for check_name, display_name in self.checks.items():
            # Get values for this check across all servers
            check_results = [
                getattr(server, check_name) for server in self.servers.values()
            ]

            # Get server hostnames for mapping
            hostnames = list(self.servers.keys())

            # Determine if this check is consistent
            is_consistent = self.is_consistent(check_name, check_results)
            state = "OK" if is_consistent else "FAIL"

            # Update summary counters
            if is_consistent:
                structured_data["summary"]["consistent_checks"] += 1
            else:
                structured_data["summary"]["inconsistent_checks"] += 1

            # Create the check result structure
            check_data: Dict[str, Any] = {
                "name": check_name,
                "display_name": display_name,
                "state": state,
                "is_consistent": is_consistent,
                "values": {},
            }

            # Add server-specific values
            for i, hostname in enumerate(hostnames):
                value = check_results[i]
                # Handle different types for serialization
                if isinstance(value, (str, int, float, bool)) or value is None:
                    check_data["values"][hostname] = value
                else:
                    # Convert non-serializable values to string
                    check_data["values"][hostname] = str(value)

            structured_data["checks"].append(check_data)

        return structured_data

    def output_structured_data(self, log: logging.Logger, format_type: str) -> None:
        """
        Output structured data in the specified format.

        Args:
            log: Logger instance for output
            format_type: The output format ('json' or 'yaml')
        """
        # Get structured data
        data = self.get_structured_data()

        # Fill in additional data
        import datetime

        data["timestamp"] = datetime.datetime.now().isoformat()

        # Use domain from first server if available
        if self.servers:
            first_server = next(iter(self.servers.values()))
            if hasattr(first_server, "domain"):
                data["domain"] = first_server.domain

        # Output in the specified format
        if format_type.lower() == "json":
            output = json.dumps(data, indent=2)
            log.info("\nConsistency check results (JSON):\n%s", output)
            if not self.args.debug and not self.args.quiet:
                print(output)
        elif format_type.lower() == "yaml":
            output = yaml.dump(data, default_flow_style=False)
            log.info("\nConsistency check results (YAML):\n%s", output)
            if not self.args.debug and not self.args.quiet:
                print(output)
        else:
            log.error(f"Unsupported output format: {format_type}")
            if not self.args.debug and not self.args.quiet:
                print(f"Error: Unsupported output format: {format_type}")


class Application:
    """
    Main application class for freeipaconsistencycheck.

    This class handles initialization, setup, and execution of the
    consistency checking application. It serves as the central orchestrator
    for the entire application flow.

    Attributes:
        app_name (str): Name of the application executable
        app_dir (str): Directory containing the application
        args (CommandLineArgs): Processed command-line arguments
        log (logging.Logger): Configured logger
        config (Config): Application configuration
        servers (OrderedDict): Dictionary of FreeIPA server connections
        checker (ConsistencyChecker): Consistency checker instance
    """

    def __init__(self):
        """
        Initialize the application.

        Sets up the application environment, including command-line argument
        parsing, logging configuration, server connections, and consistency
        checker initialization.

        Raises:
            ConfigError: If configuration validation fails
            ValueError: If server initialization fails
        """
        # Determine application name and directory
        self.app_name = os.path.basename(sys.modules["__main__"].__file__)
        self.app_dir = os.path.dirname(os.path.realpath(__file__))

        # Parse command line arguments
        self.args = parse_arguments(self.app_name, __version__)

        # Set up logging
        self.log = setup_logger(
            self.app_name,  # Application name for logger identification
            self.args,  # Command-line arguments with logging options
        )

        self.log.debug(f"Command-line arguments: {self.args}")
        self.log.debug("Initializing application...")

        # Load configuration
        try:
            self.config = Config(
                app_name=self.app_name,
                log=self.log,
                domain_arg=self.args.domain,
                hosts_arg=self.args.hosts,
                binddn_arg=self.args.binddn,
                bindpw_arg=self.args.bindpw,
            )
        except ConfigError as e:
            self.log.critical(f"Configuration error: {e}")
            raise

        # Find FreeIPA servers if not specified
        if not self.config.hosts:
            self.log.debug("No servers specified, searching in DNS...")
            dns_hosts = find_ipa_servers(self.config.domain, self.log)

            if not dns_hosts:
                self.log.critical(
                    f"No IPA servers found in DNS for domain {self.config.domain}"
                )
                raise ValueError(
                    f"No IPA servers found for domain {self.config.domain}"
                )

            self.config.hosts = dns_hosts
            self.log.info(f"Found servers via DNS: {', '.join(self.config.hosts)}")

        self.log.debug(f"IPA domain: {self.config.domain}")
        self.log.debug(f"IPA servers: {', '.join(self.config.hosts)}")

        # Initialize FreeIPA server connections
        self.servers = OrderedDict()
        connection_errors = []

        # Start the loading indicator only when not in debug mode
        loader = LoadingIndicator("Connecting to FreeIPA servers")
        if (
            not self.args.debug
        ):  # Don't show loader in debug mode because it conflicts with logs
            loader.start()

        try:
            for host in self.config.hosts:
                try:
                    self.log.debug(f"Connecting to server: {host}")
                    self.servers[host] = FreeIPAServer(
                        host, self.config.domain, self.config.binddn, self.config.bindpw
                    )
                except Exception as e:
                    self.log.error(f"Failed to connect to {host}: {e}")
                    connection_errors.append((host, str(e)))
        finally:
            # Stop the loading indicator before proceeding
            loader.stop()

        # Check if we have any working servers
        if not self.servers:
            error_details = "; ".join(
                [f"{host}: {error}" for host, error in connection_errors]
            )
            self.log.critical(f"Failed to connect to any servers: {error_details}")
            raise ValueError("Failed to connect to any FreeIPA servers")

        # If some servers failed but others succeeded, log a warning
        if connection_errors and len(connection_errors) < len(self.config.hosts):
            self.log.warning(
                f"Some servers could not be contacted: {', '.join(host for host, _ in connection_errors)}"
            )

        # Create consistency checker
        self.checker = ConsistencyChecker(self.servers, self.args)

    def run(self) -> int:
        """
        Run the application.

        Execute the application in either standard mode (displaying a table of
        consistency results) or structured output mode (JSON/YAML).

        Returns:
            Exit code (0 for success, non-zero for errors)

        Notes:
            - In standard mode, displays a formatted table of results
            - In structured mode, provides JSON or YAML output
            - Returns appropriate exit codes for shell integration
        """
        self.log.debug("Starting consistency check execution...")

        try:
            if self.args.output_format:
                self.log.debug(
                    f"Running in structured output mode, format: {self.args.output_format}"
                )
                self.checker.output_structured_data(self.log, self.args.output_format)
                return 0
            else:
                self.log.debug("Running in standard CLI mode")
                self.checker.print_table(self.log)
                return 0
        except KeyboardInterrupt:
            self.log.info("Operation interrupted by user")
            return 130
        except Exception as e:
            # This line is crucial for the test - make sure it's logging at CRITICAL level
            self.log.critical(f"Error during execution: {e}", exc_info=True)
            return 1
        finally:
            self.log.debug("Finished consistency check execution")


def main() -> int:
    """
    Main entry point for the application.

    This function creates and runs the Application instance, handling top-level
    exceptions and ensuring proper exit codes are returned.

    Returns:
        Exit code (0 for success, non-zero for errors)

    Notes:
        - Creates and runs the Application instance
        - Handles KeyboardInterrupt (Ctrl+C) gracefully
        - Catches and logs any unhandled exceptions
        - Returns appropriate exit codes for shell integration
    """
    try:
        app = Application()
        return app.run()
    except KeyboardInterrupt:
        # Handle keyboard interrupt (Ctrl+C)
        print("\nOperation terminated by user", file=sys.stderr)
        return 130
    except ConfigError as e:
        # Configuration errors were already logged in Application.__init__
        return 78  # EX_CONFIG in sysexits.h
    except ValueError as e:
        # Value errors (like missing servers) were already logged
        return 64  # EX_USAGE in sysexits.h
    except Exception as e:
        # Unexpected errors
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
