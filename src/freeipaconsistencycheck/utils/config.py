"""
Configuration handling for the freeipaconsistencycheck package.

This module provides functions to load, validate, and access application
configuration settings from files, environment variables, and command line arguments.
"""

import os
import logging
from typing import List, Optional, Tuple, Union, Any
import configparser

APP_CONFIG_DIR = "freeipaconsistencycheck"


class ConfigError(Exception):
    """Raised when there's an issue with configuration loading or validation."""

    pass


def get_config_file_path(app_name: str) -> str:
    """
    Determine the path to the configuration file based on XDG standards.

    Args:
        app_name: The name of the application

    Returns:
        str: The full path to the configuration file
    """
    # Follow XDG Base Directory Specification
    config_dir = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
    )

    return os.path.join(config_dir, APP_CONFIG_DIR, app_name)


def create_default_config(config_file: Union[str, Any], log: logging.Logger) -> None:
    """
    Create a default configuration file if one doesn't exist.

    Args:
        config_file: Path to the configuration file
        log: Logger instance for recording actions
    """
    # Ensure the directory exists
    directory = os.path.dirname(str(config_file))
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Create a default configuration
    config = configparser.ConfigParser()
    config.add_section("IPA")
    config.set("IPA", "DOMAIN", "ipa.example.com")
    config.set("IPA", "HOSTS", "ipa01, ipa02, ipa03, ipa04, ipa05, ipa06")
    config.set("IPA", "BINDDN", "cn=Directory Manager")
    config.set("IPA", "BINDPW", "example123")

    # Write the configuration to file
    with open(str(config_file), "w") as cfg_file:
        config.write(cfg_file)

    log.info(f"Initial config saved to {config_file} - PLEASE EDIT IT!")


def load_config(
    app_name: str,
    log: logging.Logger,
    domain_arg: Optional[str] = None,
    hosts_arg: Optional[List[str]] = None,
    binddn_arg: Optional[str] = None,
    bindpw_arg: Optional[str] = None,
    skip_notice: bool = False,
) -> Tuple[Optional[str], List[str], Optional[str], Optional[str]]:
    """
    Load configuration from file, with optional overrides from arguments.

    This function first attempts to load settings from a config file. If specified,
    command line arguments override the file-based settings. If no config file exists,
    a template is created.

    Args:
        app_name: Name of the application (used for config file naming)
        log: Logger instance for recording actions
        domain_arg: Override for IPA domain from command line
        hosts_arg: Override for IPA hosts from command line
        binddn_arg: Override for bind DN from command line
        bindpw_arg: Override for bind password from command line
        skip_notice: Whether to skip printing notices about example config

    Returns:
        Tuple containing domain, hosts list, bind DN, and bind password
    """
    # Initialize return values
    domain: Optional[str] = None
    hosts: List[str] = []  # Add type annotation here
    binddn: str = "cn=Directory Manager"  # Default bind DN
    bindpw: Optional[str] = None

    # Determine config file path
    config_file = get_config_file_path(app_name)
    log.debug(f"Config file path: {config_file}")

    # Create default config if it doesn't exist
    # Keep this here for test compatibility
    if not os.path.exists(config_file):
        log.debug(f"Config file not found at {config_file}")
        create_default_config(config_file, log)
        # Don't exit here - continue with loading to maintain compatibility
        if not skip_notice:
            log.info(f"Please edit the config file at {config_file} and run again")

    # Load the configuration file if it now exists
    if os.path.exists(config_file):
        log.debug(f"Loading configuration file {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file)

        # Check if the config file still has example values
        is_example_config = False
        with open(config_file, "r") as file:
            config_content = file.read()
            if "example" in config_content:
                is_example_config = True
                # Use info level instead of debug to make it visible to all users
                log.info(f"Initial config found in {config_file} - PLEASE EDIT IT!")
                if not skip_notice:
                    # Print directly to ensure users see it
                    print(f"\nNOTICE: Using example configuration from {config_file}")
                    print(
                        "Please edit this file with your actual FreeIPA server details.\n"
                    )

        # Extract values from config if IPA section exists
        if config.has_section("IPA"):
            if config.has_option("IPA", "DOMAIN"):
                domain = config.get("IPA", "DOMAIN")
                log.debug(f"DOMAIN = {domain}")
            else:
                log.debug("IPA.DOMAIN not set in config")

            if config.has_option("IPA", "HOSTS"):
                hosts_config = config.get("IPA", "HOSTS")
                log.debug(f"HOSTS = {hosts_config}")
                hosts = hosts_config.replace(",", " ").split()
            else:
                log.debug("IPA.HOSTS not set in config")

            if config.has_option("IPA", "BINDDN"):
                binddn = config.get("IPA", "BINDDN")
                log.debug(f"BINDDN = {binddn}")
            else:
                log.debug("IPA.BINDDN not set in config")

            if config.has_option("IPA", "BINDPW"):
                bindpw = config.get("IPA", "BINDPW")
                log.debug("BINDPW = ********")
            else:
                log.debug("IPA.BINDPW not set in config")
        else:
            log.debug("Config file has no IPA section")

    # Override with command line arguments if provided
    if domain_arg:
        log.debug("Domain set by argument")
        domain = domain_arg

    if hosts_arg:
        log.debug("Server list set by argument")
        hosts = hosts_arg

    if binddn_arg:
        log.debug("Bind DN set by argument")
        binddn = binddn_arg

    if bindpw_arg:
        log.debug("Bind password set by argument")
        bindpw = bindpw_arg

    return domain, hosts, binddn, bindpw


def validate_config(
    domain: Optional[str],
    hosts: List[str],
    binddn: Optional[str],
    bindpw: Optional[str],
    log: logging.Logger,
) -> None:
    """
    Validate the configuration values.

    This function checks that all required configuration values are present
    and valid. It raises ConfigError if any validation fails.

    Args:
        domain: IPA domain
        hosts: List of IPA hosts
        binddn: Bind DN
        bindpw: Bind password
        log: Logger instance for recording actions

    Raises:
        ConfigError: If any configuration value is invalid
    """
    if not domain:
        msg = "IPA domain not set"
        log.critical(msg)
        raise ConfigError(msg)

    for i, host in enumerate(hosts):
        if not host or " " in host:
            msg = f"Incorrect server name: {host}"
            log.critical(msg)
            raise ConfigError(msg)

    if not binddn:
        msg = "Bind DN not set"
        log.critical(msg)
        raise ConfigError(msg)

    if not bindpw:
        msg = "Bind password not set"
        log.critical(msg)
        raise ConfigError(msg)


class Config:
    """
    Configuration class for freeipaconsistencycheck.

    This class provides a cleaner, object-oriented interface to the application
    configuration. It handles loading, validation, and access to configuration
    values.
    """

    def __init__(
        self,
        app_name: str,
        log: logging.Logger,
        domain_arg: Optional[str] = None,
        hosts_arg: Optional[List[str]] = None,
        binddn_arg: Optional[str] = None,
        bindpw_arg: Optional[str] = None,
    ):
        """
        Initialize the configuration.

        Args:
            app_name: Name of the application
            log: Logger instance
            domain_arg: Optional domain from command line
            hosts_arg: Optional hosts list from command line
            binddn_arg: Optional bind DN from command line
            bindpw_arg: Optional bind password from command line
        """
        self.log = log
        self.app_name = app_name
        self.notice_printed = False  # Track if we've already shown the notice

        # Load configuration (which now also handles creating default config)
        self.domain, self.hosts, self.binddn, self.bindpw = load_config(
            app_name, log, domain_arg, hosts_arg, binddn_arg, bindpw_arg
        )

        # Validate configuration but don't exit on default values
        try:
            validate_config(self.domain, self.hosts, self.binddn, self.bindpw, log)
        except ConfigError as e:
            # If validation fails with default values, log but continue
            if self.domain == "ipa.example.com" and "example" in str(self.bindpw or ""):
                log.warning(f"Using example configuration: {str(e)}")
                print(f"\nWarning: {str(e)}")
                print(
                    "Continuing with example configuration for demonstration purposes.\n"
                )
            else:
                # For non-default configurations, validation errors should still fail
                print(f"\nConfiguration error: {str(e)}")
                print("Please check your configuration and try again.\n")
                raise

        log.debug(f"IPA domain: {self.domain}")
        log.debug(f'IPA servers: {", ".join(self.hosts)}')

    def as_dict(self):
        """Return the configuration as a dictionary."""
        return {
            "domain": self.domain,
            "hosts": self.hosts,
            "binddn": self.binddn,
            "bindpw": self.bindpw,
        }

    def get_host_domains(self):
        """
        Get a list of fully qualified domain names for all hosts.

        Returns:
            List of host FQDNs
        """
        host_domains = []
        for host in self.hosts:
            if "." in host:
                # Host already contains domain
                host_domains.append(host)
            else:
                # Append domain to host
                host_domains.append(f"{host}.{self.domain}")
        return host_domains
