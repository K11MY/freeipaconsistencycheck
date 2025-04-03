"""
DNS Utilities for the freeipaconsistencycheck package.

This module provides functions for DNS-related operations, particularly for
discovering FreeIPA servers through DNS SRV records. It handles DNS resolution
with proper error handling and provides a clean interface for server discovery.

The module is designed to work with both older and newer versions of the
dns.resolver library, accommodating the API changes between versions.
"""

import logging
from typing import List
import dns.resolver
import dns.exception


def find_ipa_servers(domain: str, log: logging.Logger) -> List[str]:
    """
    Find FreeIPA servers via DNS SRV records.

    This function queries DNS for the standard IPA service SRV record
    (_ldap._tcp.<domain>) to discover available IPA servers in the domain.
    It properly handles DNS resolution errors and extracts server hostnames
    from the SRV records.

    Args:
        domain: The domain name to search for IPA servers
        log: Logger instance for recording actions and errors

    Returns:
        List of IPA server hostnames found in DNS, or an empty list if none found

    Notes:
        - Uses the standard SRV record format _ldap._tcp.<domain>
        - Compatible with both older (query) and newer (resolve) dns.resolver API
        - Extracts the hostname from the SRV record target field
        - Removes trailing dots from hostnames
        - Returns an empty list if DNS query fails or no records are found

    Example:
        ```python
        servers = find_ipa_servers("example.com", logger)
        if servers:
            print(f"Found servers: {', '.join(servers)}")
        else:
            print("No IPA servers found in DNS")
        ```
    """
    log.debug(f"Searching for IPA servers in DNS for domain {domain}")
    record = f"_ldap._tcp.{domain}"
    hosts = []

    try:
        # Try the newer 'resolve' method first (dns.resolver >= 2.0.0)
        try:
            answers = dns.resolver.resolve(record, "SRV")
        except AttributeError:
            # Fall back to 'query' for older dns.resolver versions
            log.debug("Using legacy dns.resolver.query API")
            answers = dns.resolver.query(record, "SRV")

        log.debug(f"Found {len(answers)} SRV records")

        for answer in answers:
            # Extract hostname from SRV record (format: priority weight port target)
            # The hostname is the last field (target)
            answer_text = answer.to_text()
            log.debug(f"Processing SRV record: {answer_text}")

            # Parse the SRV record to extract the hostname
            parts = answer_text.split()
            if len(parts) >= 4:  # Should have at least 4 parts
                hostname = parts[3].rstrip(".")
                hosts.append(hostname)
                log.debug(f"Extracted server: {hostname}")
            else:
                log.warning(f"Malformed SRV record: {answer_text}")

    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers) as e:
        log.debug(f"DNS lookup failed: {e}")
    except dns.exception.DNSException as e:
        log.debug(f"General DNS error: {e}")

    if not hosts:
        log.debug(f"No IPA servers found in DNS for domain {domain}")
    else:
        log.debug(f'Found servers: {", ".join(hosts)}')

    return hosts


def validate_domain(domain: str, log: logging.Logger) -> bool:
    """
    Validate that a domain exists in DNS.

    This function checks if a domain exists by attempting to resolve
    its NS records. It's useful for validating domain input before
    performing more specific queries.

    Args:
        domain: The domain name to validate
        log: Logger instance for recording actions and errors

    Returns:
        True if the domain exists in DNS, False otherwise

    Notes:
        - Checks for existence of NS records for the domain
        - Compatible with both older and newer dns.resolver API
        - Returns False if any DNS resolution error occurs
    """
    log.debug(f"Validating domain existence: {domain}")

    try:
        # Try to resolve NS records for the domain
        try:
            answers = dns.resolver.resolve(domain, "NS")
        except AttributeError:
            # Fall back to 'query' for older dns.resolver versions
            answers = dns.resolver.query(domain, "NS")

        if answers:
            log.debug(f"Domain {domain} exists (found NS records)")
            return True
        return False
    except dns.exception.DNSException as e:
        log.debug(f"Domain validation failed: {e}")
        return False


def get_domain_controllers(domain: str, log: logging.Logger) -> List[str]:
    """
    Find Active Directory domain controllers via DNS SRV records.

    This function is useful when working with IPA servers that have
    trust relationships with Active Directory domains. It locates
    domain controllers by querying standard AD SRV records.

    Args:
        domain: The domain name to search for domain controllers
        log: Logger instance for recording actions and errors

    Returns:
        List of domain controller hostnames, or an empty list if none found

    Notes:
        - Queries the standard AD DC locator SRV record
        - Compatible with both older and newer dns.resolver API
        - Returns an empty list if DNS query fails or no records are found
    """
    log.debug(f"Searching for domain controllers in {domain}")
    record = f"_ldap._tcp.dc._msdcs.{domain}"
    controllers = []

    try:
        # Try the newer 'resolve' method first
        try:
            answers = dns.resolver.resolve(record, "SRV")
        except AttributeError:
            # Fall back to 'query' for older dns.resolver versions
            answers = dns.resolver.query(record, "SRV")

        for answer in answers:
            # Extract hostname from SRV record
            parts = answer.to_text().split()
            if len(parts) >= 4:
                hostname = parts[3].rstrip(".")
                controllers.append(hostname)

    except dns.exception.DNSException as e:
        log.debug(f"DNS lookup for domain controllers failed: {e}")

    return controllers
