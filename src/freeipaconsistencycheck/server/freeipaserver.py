"""
Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2017 WANdisco

This file is part of freeipaconsistencycheck.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import ldap  # type: ignore
import dns.resolver
from typing import Optional, List, Dict, Any, Union, Tuple, cast


class LDAPReferralError(Exception):
    """
    Raised when an LDAP operation results in a referral to another replica server.

    This typically occurs when a server redirects an LDAP request to another server
    that it believes holds the authoritative data for the requested entry.
    """

    pass


class FreeIPAServer:
    """
    A comprehensive interface for querying and analyzing a FreeIPA server's configuration and state.

    This class establishes an LDAP connection to a FreeIPA server and provides methods
    to retrieve various statistics and health indicators. Upon initialization, it
    performs a full analysis of the server state and stores the results as instance attributes.

    Attributes:
        hostname_short (str): Short hostname of the server (without domain suffix)
        users (str): Number of active users in the IPA domain
        susers (str): Number of staged users waiting to be activated
        pusers (str): Number of preserved (deleted) users
        hosts (int): Number of registered hosts
        services (int): Number of registered services
        ugroups (int): Number of user groups
        hgroups (str): Number of host groups
        ngroups (int): Number of netgroups
        hbac (int): Number of Host-Based Access Control rules
        sudo (int): Number of sudo rules
        zones (int): Number of DNS zones
        certs (int): Number of certificates
        conflicts (int): Number of LDAP replication conflicts
        ghosts (int): Number of ghost replicas
        bind (str): Anonymous bind status (ON, OFF, ROOTDSE, or ERROR)
        msdcs (bool): Whether Microsoft Active Directory Trust is configured
        replicas (str): Replication agreement status information
        healthy_agreements (bool): Overall health status of replication agreements
    """

    def __init__(self, host: str, domain: str, binddn: str, bindpw: str) -> None:
        """
        Initialize a connection to FreeIPA server and gather comprehensive statistics.

        This constructor establishes an LDAP connection to the specified FreeIPA server
        and performs a thorough analysis of its configuration and state. The results
        are stored as instance attributes for later access.

        Args:
            host: Hostname of the FreeIPA server (can be FQDN or short hostname)
            domain: Domain name of the FreeIPA environment
            binddn: Distinguished name for LDAP binding (e.g., "cn=Directory Manager")
            bindpw: Password for LDAP binding

        Raises:
            ValueError: If the LDAP context does not match the expected base DN
            RuntimeError: If a replica redirection occurs during initialization
        """
        # Initialize logging
        self._log = logging.getLogger(self.__class__.__module__)
        self._log.debug(f"Initialising FreeIPA server {host}")

        # Initialize connection as None
        self._conn: Optional[ldap.ldapobject.LDAPObject] = None

        # Initialize attributes with default values
        self.users: Optional[str] = None
        self.susers: Optional[str] = None
        self.pusers: Optional[str] = None
        self.hosts: Optional[int] = None
        self.services: Optional[int] = None
        self.ugroups: Optional[int] = None
        self.hgroups: Optional[str] = None
        self.ngroups: Optional[int] = None
        self.hbac: Optional[int] = 0  # Default to 0 instead of None
        self.sudo: Optional[int] = None
        self.zones: Optional[int] = None
        self.certs: Optional[int] = None
        self.conflicts: Optional[int] = None
        self.ghosts: Optional[int] = None
        self.bind: Optional[str] = None
        self.msdcs: Optional[bool] = None
        self.replicas: Optional[str] = None
        self.healthy_agreements: bool = False

        # Store connection parameters
        self._binddn = binddn
        self._bindpw = bindpw
        self._domain = domain
        self._url = f"ldaps://{host}"
        self.hostname_short = host.replace(f".{domain}", "")

        # Establish LDAP connection
        self._conn = self._get_conn()

        if not self._conn:
            return

        try:
            # Get server information
            self._fqdn = self._get_fqdn()
            self.hostname_short = self._fqdn.replace(f".{domain}", "")

            self._log.debug(
                f"FQDN: {self._fqdn}, short hostname: {self.hostname_short}"
            )

            # Build the base DN from the domain
            self._base_dn = "dc=" + self._domain.replace(".", ",dc=")

            # Verify the context matches the expected base DN
            context = self._get_context()
            if self._base_dn != context:
                self._log.critical(f"Context mismatch: {self._base_dn} vs {context}")
                raise ValueError(f"Context mismatch: {self._base_dn} vs {context}")

            # Set up base DNs for different user types
            self._active_user_base = f"cn=users,cn=accounts,{self._base_dn}"
            self._stage_user_base = (
                f"cn=staged users,cn=accounts,cn=provisioning,{self._base_dn}"
            )
            self._preserved_user_base = (
                f"cn=deleted users,cn=accounts,cn=provisioning,{self._base_dn}"
            )
            self._groups_base = f"cn=groups,cn=accounts,{self._base_dn}"

            # Collect statistics about the server - add exception handling for each method
            self.users = self._count_users(user_base="active")
            self.susers = self._count_users(user_base="stage")
            self.pusers = self._count_users(user_base="preserved")
            self.hosts = self._count_hosts()
            self.services = self._count_services()
            self.ugroups = self._count_groups()
            self.hgroups = self._count_hostgroups()
            self.ngroups = self._count_netgroups()

            # For methods that might raise exceptions during referral or other scenarios
            try:
                self.hbac = self._count_hbac_rules()
            except Exception as e:
                self._log.warning(f"Failed to count HBAC rules: {e}")
                self.hbac = 0

            try:
                self.sudo = self._count_sudo_rules()
            except Exception as e:
                self._log.warning(f"Failed to count sudo rules: {e}")
                self.sudo = 0

            # Continue with other methods with similar error handling
            self.zones = self._count_dns_zones()
            self.certs = self._count_certificates()
            self.conflicts = self._count_ldap_conflicts()
            self.ghosts = self._ghost_replicas()
            self.bind = self._anon_bind()
            self.msdcs = self._ms_adtrust()
            self.replicas, self.healthy_agreements = self._replication_agreements()

        except Exception as e:
            self._log.error(f"Error during server initialization: {e}")
            # Optionally re-raise or handle as needed

    @staticmethod
    def _get_ldap_msg(e: Exception) -> str:
        """
        Extract a human-readable error message from an LDAP exception.
        """
        msg = str(e)

        if hasattr(e, "message"):
            message = getattr(e, "message")
            if isinstance(message, dict) and "desc" in message:
                msg = message["desc"]
            elif (
                hasattr(e, "args")
                and e.args
                and isinstance(e.args[0], dict)
                and "desc" in e.args[0]
            ):
                msg = e.args[0]["desc"]
        return msg

    def _get_conn(self) -> Optional[ldap.ldapobject.LDAPObject]:
        """
        Establish an LDAP connection to the FreeIPA server.
        """
        self._log.debug("Setting up LDAP connection")
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        try:
            conn = ldap.initialize(self._url)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
            conn.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)
            conn.simple_bind_s(self._binddn, self._bindpw)
        except (ldap.SERVER_DOWN, ldap.NO_SUCH_OBJECT, ldap.INVALID_CREDENTIALS) as e:
            # Safely extract error message
            if (
                hasattr(e, "message")
                and isinstance(e.message, dict)
                and "desc" in e.message
            ):
                msg = e.message["desc"]
            elif (
                hasattr(e, "args")
                and e.args
                and isinstance(e.args[0], dict)
                and "desc" in e.args[0]
            ):
                msg = e.args[0]["desc"]
            else:
                msg = str(e)
            self._log.debug(f"{msg} ({self._url})")
            return None
        self._log.debug("LDAP connection established")
        return conn

    def _search(
        self,
        base: str,
        fltr: str,
        attrs: Optional[List[str]] = None,
        scope: int = ldap.SCOPE_SUBTREE,
    ) -> Union[List[Tuple[str, Dict[str, List[bytes]]]], bool]:
        """
        Perform an LDAP search with the given parameters.
        """
        # Add explicit None check for self._conn
        if self._conn is None:
            self._log.debug("LDAP connection is not established")
            return False

        self._log.debug(
            f"Search base: {base}, filter: {fltr}, attributes: {attrs}, scope: {scope}"
        )
        try:
            results = self._conn.search_s(base, scope, fltr, attrs)
            return results
        except (ldap.NO_SUCH_OBJECT, ldap.SERVER_DOWN) as e:
            self._log.debug(self._get_ldap_msg(e))
            return False
        except ldap.REFERRAL as e:
            self._log.critical(f"Replica {self._fqdn} is temporarily unavailable.")
            raise LDAPReferralError(
                f"Replica {self._fqdn} is temporarily unavailable. Operation was redirected."
            )

    def _safe_decode(self, value: Union[str, bytes, List[bytes]]) -> str:
        """
        Safely decode a value to a string.
        """
        if isinstance(value, list):
            # Take the first item if it's a list
            value = value[0] if value else b""

        # Decode bytes to string, or return string as-is
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def _get_fqdn(self) -> str:
        """
        Get the FQDN (Fully Qualified Domain Name) of the server from LDAP.
        """
        self._log.debug("Grabbing FQDN from LDAP")

        # Ensure self._conn is not None before searching
        if self._conn is None:
            return "unknown"

        results = self._search(
            "cn=config", "(objectClass=*)", ["nsslapd-localhost"], scope=ldap.SCOPE_BASE
        )

        if not results or not isinstance(results, list):
            return "unknown"

        # Add type handling for results
        result = results[0]
        dn, attrs = result

        # Safely decode the bytes
        fqdn_bytes = attrs.get("nsslapd-localhost", [b"unknown"])[0]
        fqdn = (
            fqdn_bytes.decode("utf-8") if isinstance(fqdn_bytes, bytes) else "unknown"
        )

        self._log.debug(fqdn)
        return fqdn

    def _get_context(self) -> str:
        """
        Get the default naming context from LDAP configuration.
        """
        self._log.debug("Grabbing default context from LDAP")

        # Ensure self._conn is not None before searching
        if self._conn is None:
            return "unknown"

        results = self._search(
            "cn=config",
            "(objectClass=*)",
            ["nsslapd-defaultnamingcontext"],
        )

        if not results or not isinstance(results, list):
            return "unknown"

        # Add type handling for results
        result = results[0]
        attrs = result[1] if isinstance(result, tuple) else {}

        # Safely decode the bytes
        context_bytes = attrs.get("nsslapd-defaultnamingcontext", [b"unknown"])[0]
        context = (
            context_bytes.decode("utf-8")
            if isinstance(context_bytes, bytes)
            else "unknown"
        )

        self._log.debug(context)
        return context

    def _count_users(self, user_base: str) -> str:
        """
        Count the number of users in the specified user base.
        """
        self._log.debug(f"Counting {user_base} users...")
        results = self._search(
            getattr(self, f"_{user_base}_user_base"),
            "(objectClass=*)",
            ["numSubordinates"],
        )

        if not results or not isinstance(results, list):
            r = "0"
        else:
            attrs = results[0][1] if isinstance(results[0], tuple) else {}
            r = self._safe_decode(attrs.get("numSubordinates", ["0"])[0])

        self._log.debug(r)
        return r

    def _count_groups(self) -> int:
        """
        Count the number of user groups in the IPA domain.
        """
        self._log.debug("Counting groups...")
        results = self._search(self._groups_base, "(objectClass=ipausergroup)")

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_hosts(self) -> int:
        """
        Count the number of host entries in the IPA domain.
        """
        self._log.debug("Counting hosts...")
        results = self._search(
            f"cn=computers,cn=accounts,{self._base_dn}", "(fqdn=*)", ["dn"]
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_services(self) -> int:
        """
        Count the number of service entries in the IPA domain.
        """
        self._log.debug("Counting services...")
        results = self._search(
            f"cn=services,cn=accounts,{self._base_dn}", "(krbprincipalname=*)", ["dn"]
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_netgroups(self) -> int:
        """
        Count the number of netgroups in the IPA domain.
        """
        self._log.debug("Counting netgroups...")
        results = self._search(
            f"cn=ng,cn=alt,{self._base_dn}",
            "(ipaUniqueID=*)",
            ["dn"],
            scope=ldap.SCOPE_ONELEVEL,
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_hostgroups(self) -> str:
        """
        Count the number of host groups in the IPA domain.
        """
        self._log.debug("Counting host groups...")
        results = self._search(
            f"cn=hostgroups,cn=accounts,{self._base_dn}",
            "(objectClass=*)",
            ["numSubordinates"],
            scope=ldap.SCOPE_BASE,
        )

        if not results or not isinstance(results, list):
            return "0"

        result = results[0]
        attrs = result[1] if isinstance(result, tuple) else {}
        r = self._safe_decode(attrs.get("numSubordinates", ["0"])[0])
        self._log.debug(r)
        return r

    def _count_hbac_rules(self) -> int:
        """
        Count the number of Host-Based Access Control (HBAC) rules in the IPA domain.
        """
        self._log.debug("Counting HBAC rules...")
        results = self._search(
            f"cn=hbac,{self._base_dn}", "(ipaUniqueID=*)", scope=ldap.SCOPE_ONELEVEL
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_sudo_rules(self) -> int:
        """
        Count the number of sudo rules in the IPA domain.
        """
        self._log.debug("Counting SUDO rules...")
        results = self._search(
            f"cn=sudorules,cn=sudo,{self._base_dn}",
            "(ipaUniqueID=*)",
            scope=ldap.SCOPE_ONELEVEL,
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_dns_zones(self) -> int:
        """
        Count the number of DNS zones in the IPA domain.
        """
        self._log.debug("Counting DNS zones...")
        results = self._search(
            f"cn=dns,{self._base_dn}",
            "(|(objectClass=idnszone)(objectClass=idnsforwardzone))",
            scope=ldap.SCOPE_ONELEVEL,
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_certificates(self) -> int:
        """
        Count the number of certificates in the IPA Certificate Authority.
        """
        self._log.debug("Counting certificates...")
        results = self._search(
            "ou=certificateRepository,ou=ca,o=ipaca",
            "(certStatus=*)",
            ["subjectName"],
            scope=ldap.SCOPE_ONELEVEL,
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_ldap_conflicts(self) -> int:
        """
        Count the number of LDAP replication conflicts in the directory.
        """
        self._log.debug("Checking for LDAP conflicts...")
        results = self._search(
            self._base_dn,
            "(|(nsds5ReplConflict=*)(&(objectclass=ldapsubentry)(nsds5ReplConflict=*)))",
            ["nsds5ReplConflict"],
        )

        if not results or not isinstance(results, list):
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _ghost_replicas(self) -> int:
        """
        Detect and count ghost replicas in the LDAP directory.
        """
        self._log.debug("Checking for ghost replicas...")
        results = self._search(
            self._base_dn,
            "(&(objectclass=nstombstone)(nsUniqueId=ffffffff-ffffffff-ffffffff-ffffffff))",
            ["nscpentrywsi"],
        )

        r = 0

        if isinstance(results, list) and results:
            dn, attrs = results[0]

            if "nscpentrywsi" in attrs:
                for attr in attrs["nscpentrywsi"]:
                    attr_str = str(attr)
                    if "replica " in attr_str and "ldap" not in attr_str:
                        r += 1

        self._log.debug(r)
        return r

    def _anon_bind(self) -> str:
        """
        Check the anonymous bind configuration for the LDAP server.
        """
        self._log.debug("Checking for anonymous bind...")
        results = self._search(
            "cn=config",
            "(objectClass=*)",
            ["nsslapd-allow-anonymous-access"],
            scope=ldap.SCOPE_BASE,
        )

        if not results or not isinstance(results, list):
            return "ERROR"

        dn, attrs = results[0]

        if "nsslapd-allow-anonymous-access" not in attrs:
            return "ERROR"

        state = self._safe_decode(attrs["nsslapd-allow-anonymous-access"][0])

        if state in ["on", "off", "rootdse"]:
            r = str(state).upper()
        else:
            r = "ERROR"

        self._log.debug(r)
        return r

    def _ms_adtrust(self) -> bool:
        """
        Check for Microsoft Active Directory Trust DNS records.
        """
        self._log.debug("Checking for MS ADTrust DNS records...")
        record = (
            f"_kerberos._tcp.Default-First-Site-Name._sites.dc._msdcs.{self._domain}"
        )

        r = False

        try:
            # Use resolve() instead of query() for newer dns.resolver versions
            try:
                answers = dns.resolver.resolve(record, "SRV")
            except AttributeError:
                # Fall back to query() for older versions
                answers = dns.resolver.query(record, "SRV")

            for answer in answers:
                if self._fqdn in answer.to_text():
                    r = True
                    break

        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
            dns.exception.DNSException,
        ):
            # Handle various DNS resolution failures
            pass

        self._log.debug(r)
        return r

    def _replication_agreements(self) -> Tuple[str, bool]:
        """
        Retrieve and evaluate the current replication agreement status for LDAP servers.
        """
        self._log.debug("Checking for replication agreements...")
        msg = []
        healthy = True
        suffix = self._base_dn.replace("=", "\\3D").replace(",", "\\2C")
        results = self._search(
            f"cn=replica,cn={suffix},cn=mapping tree,cn=config",
            "(objectClass=*)",
            ["nsDS5ReplicaHost", "nsds5replicaLastUpdateStatus"],
            scope=ldap.SCOPE_ONELEVEL,
        )

        if not results or not isinstance(results, list):
            return "No replication agreements found", False

        for result in results:
            dn, attrs = result
            if (
                "nsDS5ReplicaHost" not in attrs
                or "nsds5replicaLastUpdateStatus" not in attrs
            ):
                continue

            host = self._safe_decode(attrs["nsDS5ReplicaHost"][0])
            host = host.replace(f".{self._domain}", "")

            status = self._safe_decode(attrs["nsds5replicaLastUpdateStatus"][0])
            status = status.replace("Error ", "").partition(" ")[0].strip("()")

            if status not in ["0", "18"]:
                healthy = False

            msg.append(f"{host} {status}")

        r1 = "\n".join(msg) if msg else "No replication agreements found"
        r2 = healthy
        self._log.debug(f"{r1}, {r2}")
        return r1, r2
