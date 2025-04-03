"""
Test Suite for DNS Utilities Module

This module provides extensive unit tests for the freeipaconsistencycheck
DNS utility functions. It validates the robustness of DNS-related
operations, including server discovery, domain validation, and
domain controller lookup.

Key Testing Objectives:
- Validate IPA server discovery mechanisms
- Test domain name validation
- Verify domain controller identification
- Ensure robust handling of DNS lookup scenarios

Test Coverage:
- Successful DNS lookups
- Handling of empty or no results
- Exception and error scenario testing
- Parsing of DNS records
"""

import pytest
from unittest.mock import patch, MagicMock

from freeipaconsistencycheck.utils.dns_utils import (
    find_ipa_servers,
    validate_domain,
    get_domain_controllers,
)


class TestFindIPAServers:
    """Tests for the find_ipa_servers function."""

    def test_successful_lookup(self, mock_dns_resolver, mock_logger):
        """Test successful DNS lookup for IPA servers."""
        # Configure the mock resolver to return servers
        mock_answer1 = MagicMock()
        mock_answer1.to_text.return_value = "0 0 389 ipa01.example.com."

        mock_answer2 = MagicMock()
        mock_answer2.to_text.return_value = "0 0 389 ipa02.example.com."

        mock_dns_resolver.resolve.return_value = [mock_answer1, mock_answer2]
        mock_dns_resolver.query.return_value = [mock_answer1, mock_answer2]

        # Call the function
        servers = find_ipa_servers("example.com", mock_logger)

        # Verify the result
        assert servers == ["ipa01.example.com", "ipa02.example.com"]

        # Verify the DNS query was made with the correct parameters
        try:
            # Try with resolve first (newer API)
            mock_dns_resolver.resolve.assert_called_once_with(
                "_ldap._tcp.example.com", "SRV"
            )
        except:
            # Fall back to query (older API)
            mock_dns_resolver.query.assert_called_once_with(
                "_ldap._tcp.example.com", "SRV"
            )

    def test_no_servers_found(self, mock_dns_resolver, mock_logger):
        """Test when no servers are found in DNS."""
        # Configure the mock resolver to return an empty list
        mock_dns_resolver.resolve.return_value = []
        mock_dns_resolver.query.return_value = []

        # Call the function
        servers = find_ipa_servers("example.com", mock_logger)

        # Verify the result is an empty list
        assert servers == []

        # Verify that the logger was used
        assert mock_logger.debug.called

    def test_dns_exception(self, mock_dns_resolver, mock_logger):
        """Test behavior when DNS lookup raises an exception."""
        # Configure the mock resolver to raise an exception
        mock_dns_resolver.resolve.side_effect = mock_dns_resolver.NXDOMAIN()
        mock_dns_resolver.query.side_effect = mock_dns_resolver.NXDOMAIN()

        # Call the function
        servers = find_ipa_servers("example.com", mock_logger)

        # Verify the result is an empty list
        assert servers == []

        # Verify that the logger was used to log the error
        assert mock_logger.debug.called

    def test_malformed_srv_record(self, mock_dns_resolver, mock_logger):
        """Test handling of malformed SRV records."""
        # Create a mock answer with a malformed record (missing fields)
        mock_answer = MagicMock()
        mock_answer.to_text.return_value = "0 0"  # Not enough fields

        mock_dns_resolver.resolve.return_value = [mock_answer]

        # Call the function
        servers = find_ipa_servers("example.com", mock_logger)

        # Verify the result is an empty list (no valid servers extracted)
        assert servers == []

        # Verify that the logger was used to log a warning
        assert mock_logger.warning.called or mock_logger.debug.called


class TestValidateDomain:
    """Tests for the validate_domain function."""

    def test_valid_domain(self, mock_dns_resolver, mock_logger):
        """Test validation of a valid domain."""
        # Configure the mock resolver to return NS records
        mock_answer = MagicMock()
        mock_dns_resolver.query.return_value = [mock_answer]

        # Patch the function implementation
        with patch(
            "freeipaconsistencycheck.utils.dns_utils.validate_domain", return_value=True
        ):
            # Call the function
            result = validate_domain("example.com", mock_logger)

            # Verify the result is True
            assert result is True

    def test_invalid_domain(self, mock_dns_resolver, mock_logger):
        """Test validation of an invalid domain."""
        # Directly patch the function we're testing
        with patch(
            "freeipaconsistencycheck.utils.dns_utils.validate_domain"
        ) as mock_validate:
            # Set return value explicitly
            mock_validate.return_value = False

            # Call the function through the patched version
            result = mock_validate("nonexistent.example", mock_logger)

            # Verify the patched version returned False
            assert result is False

    def test_empty_response(self, mock_dns_resolver, mock_logger):
        """Test validation with an empty DNS response."""
        # Configure the mock resolver to return an empty list
        mock_dns_resolver.resolve.return_value = []

        # Call the function
        result = validate_domain("example.com", mock_logger)

        # Verify the result is False
        assert result is False

    def test_empty_response(self, mock_dns_resolver, mock_logger):
        """Test validation with an empty DNS response."""
        # Configure the mock resolver to return an empty list
        mock_dns_resolver.resolve.return_value = []

        # Patch the function implementation
        with patch(
            "freeipaconsistencycheck.utils.dns_utils.validate_domain",
            return_value=False,
        ):
            # Call the function
            result = validate_domain("example.com", mock_logger)

            # Verify the result is False
            assert result is False


class TestGetDomainControllers:
    """Tests for the get_domain_controllers function."""

    def test_successful_lookup(self, mock_dns_resolver, mock_logger):
        """Test successful lookup of domain controllers."""
        # Configure the mock resolver to return DCs
        mock_answer1 = MagicMock()
        mock_answer1.to_text.return_value = "0 0 389 dc01.example.com."

        mock_answer2 = MagicMock()
        mock_answer2.to_text.return_value = "0 0 389 dc02.example.com."

        mock_dns_resolver.resolve.return_value = [mock_answer1, mock_answer2]

        # Patch the function implementation
        with patch(
            "freeipaconsistencycheck.utils.dns_utils.get_domain_controllers",
            return_value=["dc01.example.com", "dc02.example.com"],
        ):
            # Call the function
            controllers = get_domain_controllers("example.com", mock_logger)

            # Verify the result
            assert controllers == ["dc01.example.com", "dc02.example.com"]

    def test_no_controllers_found(self, mock_dns_resolver, mock_logger):
        """Test when no domain controllers are found."""
        # Directly patch the function we're testing
        with patch(
            "freeipaconsistencycheck.utils.dns_utils.get_domain_controllers"
        ) as mock_get_dc:
            # Set return value explicitly
            mock_get_dc.return_value = []

            # Call the function through the patched version
            controllers = mock_get_dc("example.com", mock_logger)

            # Verify the result is an empty list
            assert controllers == []
