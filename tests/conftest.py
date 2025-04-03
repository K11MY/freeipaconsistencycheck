"""
Test Fixtures and Configuration for freeipaconsistencycheck Package

This module provides shared pytest fixtures that facilitate comprehensive
testing across the entire freeipaconsistencycheck project. These fixtures offer
standardized mock objects, sample data, and configuration helpers to
support consistent and robust testing.

Key Fixture Categories:
- Logging Mocks
- CLI Argument Simulation
- Module Mocking (LDAP, DNS)
- Sample Data Generators
- Configuration Mocking

Purpose:
- Provide reusable test components
- Standardize mock object creation
- Simplify test setup and configuration
- Enable consistent testing across different modules

Dependencies:
- pytest: Testing framework
- unittest.mock: Mocking utilities
- logging: Logging infrastructure
"""

import os
import sys
import logging
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional


@pytest.fixture
def mock_logger():
    """
    Create a mock logger that can be used in tests.

    Returns:
        MagicMock: A mock logger object with common logging methods
    """
    logger = MagicMock(spec=logging.Logger)
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    return logger


@pytest.fixture
def sample_cli_args():
    """
    Create a sample CommandLineArgs object for testing.

    Returns:
        MagicMock: Mock object with CommandLineArgs structure
    """
    args = MagicMock()
    args.domain = "example.com"
    args.hosts = ["ipa01.example.com", "ipa02.example.com"]
    args.binddn = "cn=Directory Manager"
    args.bindpw = "password123"
    args.debug = False
    args.verbose = False
    args.quiet = False
    args.log_file = None
    args.disable_header = False
    args.disable_border = False
    args.output_format = None
    return args


@pytest.fixture
def mock_ldap():
    """
    Mock the LDAP module for testing.

    Returns:
        MagicMock: A mock of the LDAP module
    """
    with patch("ldap.initialize") as mock_initialize:
        mock_conn = MagicMock()
        mock_initialize.return_value = mock_conn

        # Add common LDAP constants
        mock_ldap = MagicMock()
        mock_ldap.initialize = mock_initialize
        mock_ldap.SCOPE_BASE = 0
        mock_ldap.SCOPE_ONELEVEL = 1
        mock_ldap.SCOPE_SUBTREE = 2
        mock_ldap.OPT_REFERRALS = 8
        mock_ldap.OPT_OFF = 0
        mock_ldap.OPT_X_TLS_REQUIRE_CERT = 24
        mock_ldap.OPT_X_TLS_NEVER = 0
        mock_ldap.OPT_NETWORK_TIMEOUT = 5

        # Exception classes
        mock_ldap.SERVER_DOWN = type("SERVER_DOWN", (Exception,), {})
        mock_ldap.NO_SUCH_OBJECT = type("NO_SUCH_OBJECT", (Exception,), {})
        mock_ldap.INVALID_CREDENTIALS = type("INVALID_CREDENTIALS", (Exception,), {})
        mock_ldap.REFERRAL = type("REFERRAL", (Exception,), {})

        yield mock_ldap


@pytest.fixture
def mock_dns_resolver():
    """
    Mock the dns.resolver module for testing.

    Returns:
        MagicMock: A mock of the dns.resolver module
    """
    with patch("dns.resolver") as mock_resolver:
        # Create mock exceptions
        mock_resolver.NXDOMAIN = type("NXDOMAIN", (Exception,), {})
        mock_resolver.NoNameservers = type("NoNameservers", (Exception,), {})

        # Create a mock answer
        mock_answer = MagicMock()
        mock_answer.to_text.return_value = "0 0 389 ipa01.example.com."

        # Configure resolver.query/resolve to return the mock answer
        mock_resolver.query = MagicMock(return_value=[mock_answer])
        mock_resolver.resolve = MagicMock(return_value=[mock_answer])

        yield mock_resolver


@pytest.fixture
def sample_server_data():
    """
    Provide sample server data for testing.

    Returns:
        dict: Sample server attributes and values
    """
    return {
        "users": "1234",
        "susers": "12",
        "pusers": "5",
        "hosts": 42,
        "services": 56,
        "ugroups": 98,
        "hgroups": "23",
        "ngroups": 7,
        "hbac": 15,
        "sudo": 12,
        "zones": 3,
        "certs": 42,
        "conflicts": 0,
        "ghosts": 0,
        "bind": "OFF",
        "msdcs": False,
        "replicas": "server1 0\nserver2 0",
        "healthy_agreements": True,
        "hostname_short": "ipa01",
    }


@pytest.fixture
def mock_config():
    """
    Create a mock Config object.

    Returns:
        MagicMock: A mock Config object with standard attributes
    """
    config = MagicMock()
    config.domain = "example.com"
    config.hosts = ["ipa01.example.com", "ipa02.example.com"]
    config.binddn = "cn=Directory Manager"
    config.bindpw = "password123"
    return config


@pytest.fixture
def mock_freeipa_server(sample_server_data):
    """
    Create a mock FreeIPAServer object.

    Args:
        sample_server_data: Fixture providing sample server data

    Returns:
        MagicMock: A mock FreeIPAServer object with sample data
    """
    server = MagicMock()

    # Set all attributes from sample data
    for attr, value in sample_server_data.items():
        setattr(server, attr, value)

    return server
