"""
Check IPA Consistency Tool

A comprehensive tool for verifying consistency across multiple FreeIPA servers
in a replication topology. This package helps system administrators identify
and troubleshoot replication issues, configuration discrepancies, and other
consistency problems.

Features:
---------
- Compare user, group, and host counts across servers
- Verify replication agreement health
- Check for LDAP conflicts and ghost replicas
- Monitor certificate consistency
- Identify DNS zone synchronization issues

Usage:
------
Command-line interface:
    cipa --domain example.com --hosts ipa01.example.com ipa02.example.com

As a Python library:
    >>> from freeipaconsistencycheck.server import FreeIPAServer
    >>> server = FreeIPAServer('ipa01.example.com', 'example.com', 'cn=Directory Manager', 'password')
    >>> print(f"Users: {server.users}, Hosts: {server.hosts}")

For more information, please refer to the project documentation.
"""

# Import and expose version information
from .__version__ import __version__

# Import key classes directly (avoiding circular imports)
try:
    from .server import FreeIPAServer

    __all__ = ["__version__", "FreeIPAServer"]
except ImportError:
    __all__ = ["__version__"]
