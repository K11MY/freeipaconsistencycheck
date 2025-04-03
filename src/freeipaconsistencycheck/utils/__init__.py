"""
Utility functions for the freeipaconsistencycheck package.

This package provides core utilities used throughout the application for:

- Command Line Interface (cli): Parsing and processing command-line arguments
- Configuration (config): Loading and validating application configuration
- Logging (logger): Setting up and configuring application logging
- DNS Utilities (dns_utils): Performing DNS-related operations

These utilities form the foundation of the application's infrastructure and
provide consistent interfaces for common tasks across the codebase.

Example Usage:
-------------
    # Command line parsing
    from freeipaconsistencycheck.utils import parse_arguments
    args = parse_arguments(app_name, version)

    # Configuration
    from freeipaconsistencycheck.utils import Config
    config = Config(app_name, logger, domain_arg=args.domain)

    # Logging
    from freeipaconsistencycheck.utils import setup_logger
    logger = setup_logger(app_name, args)

    # DNS operations
    from freeipaconsistencycheck.utils import find_ipa_servers
    servers = find_ipa_servers(domain, logger)
"""

# Version of the utils package (for internal reference)
__version__ = "0.2.0"

#
# Command Line Interface Utilities
#
from .cli import parse_arguments, CommandLineArgs

#
# Configuration Utilities
#
from .config import Config, ConfigError

#
# Logging Utilities
#
from .logger import setup_logger

#
# DNS Utilities
#
from .dns_utils import find_ipa_servers

#
# Loading Utilities
#
from .loading_indicator import LoadingIndicator

# Define public API
__all__ = [
    # CLI utilities
    "parse_arguments",
    "CommandLineArgs",
    # Configuration utilities
    "Config",
    "ConfigError",
    # Logging utilities
    "setup_logger",
    # DNS utilities
    "find_ipa_servers",
    # LoadingIndicator
    "LoadingIndicator",
]

# Quick access to module names for internal use
MODULES = {
    "cli": "Command Line Interface utilities",
    "config": "Configuration management utilities",
    "logger": "Logging setup and configuration",
    "dns_utils": "DNS lookup and resolution utilities",
}


def get_utilities_info():
    """
    Get information about available utility modules.

    Returns:
        dict: Information about the utility modules and their purposes
    """
    return {
        "package": "freeipaconsistencycheck.utils",
        "version": __version__,
        "modules": MODULES,
        "available_functions": sorted(__all__),
    }
