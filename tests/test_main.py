"""
Comprehensive Test Suite for the Main Application Module

This module provides extensive unit tests for the freeipaconsistencycheck
main application functionality, covering key components of the
application's core logic and error handling mechanisms.

Key Testing Objectives:
- Validate ConsistencyChecker class behavior
- Test Application class initialization and runtime scenarios
- Verify main function error handling
- Ensure robust handling of different execution scenarios

Test Coverage:
- Consistency checking across multiple servers
- Structured output functionality (JSON/YAML)
- Standard output mode
- Error handling for various exception scenarios
- Command-line argument processing
- Server discovery and connection
"""

import os
import sys
import json
import yaml
import pytest
from unittest.mock import patch, MagicMock, call
from collections import OrderedDict

from freeipaconsistencycheck.main import Application, ConsistencyChecker, main


class TestConsistencyChecker:
    """Tests for the ConsistencyChecker class."""

    def test_initialization(self, sample_cli_args, mock_freeipa_server):
        """Test initialization of ConsistencyChecker."""
        # Create a dictionary of servers
        servers = {
            "server1.example.com": mock_freeipa_server,
            "server2.example.com": mock_freeipa_server,
        }

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Verify the attributes were set correctly
        assert checker.servers == servers
        assert checker.args == sample_cli_args
        assert len(checker.checks) > 0
        assert "users" in checker.checks
        assert "hosts" in checker.checks
        assert "replicas" in checker.checks

    def test_initialization_empty_servers(self, sample_cli_args):
        """Test initialization with empty servers dictionary."""
        # Attempt to create a ConsistencyChecker with empty servers
        with pytest.raises(ValueError) as excinfo:
            ConsistencyChecker({}, sample_cli_args)

        # Verify the exception message
        assert "No servers provided" in str(excinfo.value)

    def test_is_consistent_default_case(self, sample_cli_args, mock_freeipa_server):
        """Test is_consistent method for the default case."""
        # Create a dictionary of servers with identical values
        servers = {
            "server1.example.com": mock_freeipa_server,
            "server2.example.com": mock_freeipa_server,
        }

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Test consistency check with identical values
        check_results = [100, 100, 100]
        assert checker.is_consistent("users", check_results) is True

        # Test consistency check with different values
        check_results = [100, 200, 100]
        assert checker.is_consistent("users", check_results) is False

        # Test consistency check with None values
        check_results = [100, None, 100]
        assert checker.is_consistent("users", check_results) is False

        # Test with empty results
        assert checker.is_consistent("users", []) is False

    def test_is_consistent_conflicts(self, sample_cli_args):
        """Test is_consistent method for conflicts check."""
        # Create mock servers with different conflicts values
        server1 = MagicMock()
        server1.conflicts = 0

        server2 = MagicMock()
        server2.conflicts = 0

        servers = {"server1.example.com": server1, "server2.example.com": server2}

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Test consistency check with no conflicts (should be consistent)
        assert checker.is_consistent("conflicts", [0, 0]) is True

        # Modify one server to have conflicts
        server2.conflicts = 2

        # Test consistency check with conflicts (should be inconsistent)
        assert checker.is_consistent("conflicts", [0, 2]) is False

    def test_is_consistent_ghosts(self, sample_cli_args):
        """Test is_consistent method for ghosts check."""
        # Create mock servers with different ghost values
        server1 = MagicMock()
        server1.ghosts = 0

        server2 = MagicMock()
        server2.ghosts = 0

        servers = {"server1.example.com": server1, "server2.example.com": server2}

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Test consistency check with no ghosts (should be consistent)
        assert checker.is_consistent("ghosts", [0, 0]) is True

        # Modify one server to have ghosts
        server2.ghosts = 1

        # Test consistency check with ghosts (should be inconsistent)
        assert checker.is_consistent("ghosts", [0, 1]) is False

    def test_is_consistent_replicas(self, sample_cli_args):
        """Test is_consistent method for replicas check."""
        # Create mock servers with different replica health
        server1 = MagicMock()
        server1.healthy_agreements = True

        server2 = MagicMock()
        server2.healthy_agreements = True

        servers = {"server1.example.com": server1, "server2.example.com": server2}

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Test consistency check with healthy replicas (should be consistent)
        assert checker.is_consistent("replicas", ["status1", "status2"]) is True

        # Modify one server to have unhealthy agreements
        server2.healthy_agreements = False

        # Test consistency check with unhealthy replicas (should be inconsistent)
        assert checker.is_consistent("replicas", ["status1", "status2"]) is False

    @patch("prettytable.PrettyTable")
    def test_print_table(self, mock_prettytable_class, sample_cli_args, mock_logger):
        """Test print_table method."""
        # Create mock servers with different values
        server1 = MagicMock()
        server1.hostname_short = "ipa01"
        server1.users = "100"
        server1.hosts = 5

        server2 = MagicMock()
        server2.hostname_short = "ipa02"
        server2.users = "100"
        server2.hosts = 6

        servers = OrderedDict(
            [("server1.example.com", server1), ("server2.example.com", server2)]
        )

        # Mock PrettyTable instance
        mock_table = MagicMock()
        mock_prettytable_class.return_value = mock_table

        # Create a ConsistencyChecker instance with limited checks for testing
        checker = ConsistencyChecker(servers, sample_cli_args)
        checker.checks = OrderedDict([("users", "Active Users"), ("hosts", "Hosts")])

        # Call the method - this should try to create the table
        checker.print_table(mock_logger)

        # Verify that *something* was printed via logger
        assert mock_logger.info.called or mock_logger.debug.called

    def test_get_structured_data(self, sample_cli_args, mock_freeipa_server):
        """Test get_structured_data method."""
        # Create a dictionary of servers
        server1 = MagicMock()
        server1.hostname_short = "ipa01"
        server1.users = "100"
        server1.hosts = 5
        server1.conflicts = 0
        server1.ghosts = 0
        server1.healthy_agreements = True

        server2 = MagicMock()
        server2.hostname_short = "ipa02"
        server2.users = "100"
        server2.hosts = 6  # Different from server1
        server2.conflicts = 0
        server2.ghosts = 0
        server2.healthy_agreements = True

        servers = OrderedDict(
            [("server1.example.com", server1), ("server2.example.com", server2)]
        )

        # Create a ConsistencyChecker instance with limited checks for testing
        checker = ConsistencyChecker(servers, sample_cli_args)
        checker.checks = OrderedDict(
            [
                ("users", "Active Users"),
                ("hosts", "Hosts"),
            ]
        )

        # Get structured data
        data = checker.get_structured_data()

        # Verify the structure
        assert "servers" in data
        assert "checks" in data
        assert "summary" in data

        # Verify server information
        assert len(data["servers"]) == 2
        assert data["servers"][0]["hostname"] == "server1.example.com"
        assert data["servers"][1]["hostname"] == "server2.example.com"

        # Verify check information
        assert len(data["checks"]) == 2

        # Find the users check
        users_check = next(
            check for check in data["checks"] if check["name"] == "users"
        )
        hosts_check = next(
            check for check in data["checks"] if check["name"] == "hosts"
        )

        assert users_check["is_consistent"] is True
        assert hosts_check["is_consistent"] is False

        # Verify values
        assert users_check["values"]["server1.example.com"] == "100"
        assert users_check["values"]["server2.example.com"] == "100"
        assert hosts_check["values"]["server1.example.com"] == 5
        assert hosts_check["values"]["server2.example.com"] == 6

        # Verify summary
        assert data["summary"]["total_checks"] == 2
        assert data["summary"]["consistent_checks"] == 1
        assert data["summary"]["inconsistent_checks"] == 1

    @patch("json.dumps")
    def test_output_structured_data_json(
        self, mock_json_dumps, sample_cli_args, mock_logger
    ):
        """Test output_structured_data method with JSON format."""
        # Create a dictionary of servers
        servers = {
            "server1.example.com": MagicMock(
                hostname_short="ipa01", domain="example.com"
            ),
            "server2.example.com": MagicMock(
                hostname_short="ipa02", domain="example.com"
            ),
        }

        # Create a ConsistencyChecker instance with mock get_structured_data
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Mock the get_structured_data method
        checker.get_structured_data = MagicMock(return_value={"key": "value"})

        # Mock json.dumps to return a known value
        mock_json_dumps.return_value = '{"key": "value"}'

        # Call the method with json format
        checker.output_structured_data(mock_logger, "json")

        # Verify that json.dumps was called with the structured data
        mock_json_dumps.assert_called_once()

        # Verify that the result was logged
        mock_logger.info.assert_called_once()
        assert "JSON" in mock_logger.info.call_args[0][0]

    @patch("yaml.dump")
    def test_output_structured_data_yaml(
        self, mock_yaml_dump, sample_cli_args, mock_logger
    ):
        """Test output_structured_data method with YAML format."""
        # Create a dictionary of servers
        servers = {
            "server1.example.com": MagicMock(
                hostname_short="ipa01", domain="example.com"
            ),
            "server2.example.com": MagicMock(
                hostname_short="ipa02", domain="example.com"
            ),
        }

        # Create a ConsistencyChecker instance with mock get_structured_data
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Mock the get_structured_data method
        checker.get_structured_data = MagicMock(return_value={"key": "value"})

        # Mock yaml.dump to return a known value
        mock_yaml_dump.return_value = "key: value\n"

        # Call the method with yaml format
        checker.output_structured_data(mock_logger, "yaml")

        # Verify that yaml.dump was called with the structured data
        mock_yaml_dump.assert_called_once()

        # Verify that the result was logged
        mock_logger.info.assert_called_once()
        assert "YAML" in mock_logger.info.call_args[0][0]

    def test_output_structured_data_invalid_format(self, sample_cli_args, mock_logger):
        """Test output_structured_data method with invalid format."""
        # Create a dictionary of servers
        servers = {
            "server1.example.com": MagicMock(hostname_short="ipa01"),
            "server2.example.com": MagicMock(hostname_short="ipa02"),
        }

        # Create a ConsistencyChecker instance
        checker = ConsistencyChecker(servers, sample_cli_args)

        # Call the method with an invalid format
        checker.output_structured_data(mock_logger, "invalid")

        # Verify that an error was logged
        mock_logger.error.assert_called_once()
        assert "Unsupported output format" in mock_logger.error.call_args[0][0]


class TestApplication:
    """Tests for the Application class."""

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.FreeIPAServer")
    def test_initialization_success(
        self,
        mock_freeipa_server_class,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test successful initialization of Application."""
        # Mock command-line arguments
        mock_args = MagicMock()
        mock_args.domain = "example.com"
        mock_args.hosts = ["server1.example.com", "server2.example.com"]
        mock_args.binddn = "cn=Directory Manager"
        mock_args.bindpw = "secret"
        mock_parse_arguments.return_value = mock_args

        # Mock logger
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        # Mock Config
        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = ["server1.example.com", "server2.example.com"]
        mock_config.binddn = "cn=Directory Manager"
        mock_config.bindpw = "secret"
        mock_config_class.return_value = mock_config

        # Mock FreeIPAServer
        mock_server = MagicMock()
        mock_freeipa_server_class.return_value = mock_server

        # Create an Application instance
        app = Application()

        # Verify the initialization was successful
        assert app.args == mock_args
        assert app.log == mock_logger
        assert app.config == mock_config
        assert len(app.servers) == 2
        assert isinstance(app.checker, ConsistencyChecker)

        # Verify FreeIPAServer was created for each host
        assert mock_freeipa_server_class.call_count == 2

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.find_ipa_servers")
    def test_find_servers_in_dns(
        self,
        mock_find_ipa_servers,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test finding servers in DNS when none are specified."""
        # Mock command-line arguments
        mock_args = MagicMock()
        mock_parse_arguments.return_value = mock_args

        # Mock logger
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        # Mock Config with no hosts
        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = []
        mock_config_class.return_value = mock_config

        # Mock find_ipa_servers to return some servers
        mock_find_ipa_servers.return_value = ["dns1.example.com", "dns2.example.com"]

        # Mock FreeIPAServer
        with patch(
            "freeipaconsistencycheck.main.FreeIPAServer"
        ) as mock_freeipa_server_class:
            mock_server = MagicMock()
            mock_freeipa_server_class.return_value = mock_server

            # Create an Application instance
            app = Application()

            # Verify servers were found in DNS
            mock_find_ipa_servers.assert_called_once_with("example.com", mock_logger)

            # Verify the hosts list was updated
            assert mock_config.hosts == ["dns1.example.com", "dns2.example.com"]

            # Verify FreeIPAServer was created for each DNS-found host
            assert mock_freeipa_server_class.call_count == 2

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.find_ipa_servers")
    def test_no_servers_found(
        self,
        mock_find_ipa_servers,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test error handling when no servers are found."""
        # Mock command-line arguments
        mock_args = MagicMock()
        mock_parse_arguments.return_value = mock_args

        # Mock logger
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        # Mock Config with no hosts
        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = []
        mock_config_class.return_value = mock_config

        # Mock find_ipa_servers to return empty list
        mock_find_ipa_servers.return_value = []

        # Create an Application instance - should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            Application()

        # Verify the error message
        assert "No IPA servers found" in str(excinfo.value)

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.FreeIPAServer")
    def test_run_standard_mode(
        self,
        mock_freeipa_server_class,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test running the application in standard mode."""
        # Set up mocks for initialization
        mock_args = MagicMock()
        mock_args.output_format = None
        mock_parse_arguments.return_value = mock_args

        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = ["server1.example.com"]
        mock_config_class.return_value = mock_config

        mock_server = MagicMock()
        mock_freeipa_server_class.return_value = mock_server

        # Mock the ConsistencyChecker
        with patch(
            "freeipaconsistencycheck.main.ConsistencyChecker"
        ) as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker_class.return_value = mock_checker

            # Create an Application instance
            app = Application()

            # Run the application
            result = app.run()

            # Verify the checker's print_table method was called
            mock_checker.print_table.assert_called_once_with(mock_logger)

            # Verify the structured output method was not called
            mock_checker.output_structured_data.assert_not_called()

            # Verify the return value
            assert result == 0

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.FreeIPAServer")
    def test_run_json_mode(
        self,
        mock_freeipa_server_class,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test running the application in JSON output mode."""
        # Set up mocks for initialization
        mock_args = MagicMock()
        mock_args.output_format = "json"
        mock_parse_arguments.return_value = mock_args

        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = ["server1.example.com"]
        mock_config_class.return_value = mock_config

        mock_server = MagicMock()
        mock_freeipa_server_class.return_value = mock_server

        # Mock the ConsistencyChecker
        with patch(
            "freeipaconsistencycheck.main.ConsistencyChecker"
        ) as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker_class.return_value = mock_checker

            # Create an Application instance
            app = Application()

            # Run the application
            result = app.run()

            # Verify the output_structured_data method was called with JSON format
            mock_checker.output_structured_data.assert_called_once_with(
                mock_logger, "json"
            )

            # Verify the print_table method was not called
            mock_checker.print_table.assert_not_called()

            # Verify the return value
            assert result == 0

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.FreeIPAServer")
    def test_run_yaml_mode(
        self,
        mock_freeipa_server_class,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test running the application in YAML output mode."""
        # Set up mocks for initialization
        mock_args = MagicMock()
        mock_args.output_format = "yaml"
        mock_parse_arguments.return_value = mock_args

        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = ["server1.example.com"]
        mock_config_class.return_value = mock_config

        mock_server = MagicMock()
        mock_freeipa_server_class.return_value = mock_server

        # Mock the ConsistencyChecker
        with patch(
            "freeipaconsistencycheck.main.ConsistencyChecker"
        ) as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker_class.return_value = mock_checker

            # Create an Application instance
            app = Application()

            # Run the application
            result = app.run()

            # Verify the output_structured_data method was called with YAML format
            mock_checker.output_structured_data.assert_called_once_with(
                mock_logger, "yaml"
            )

            # Verify the print_table method was not called
            mock_checker.print_table.assert_not_called()

            # Verify the return value
            assert result == 0

    @patch("freeipaconsistencycheck.main.parse_arguments")
    @patch("freeipaconsistencycheck.main.setup_logger")
    @patch("freeipaconsistencycheck.main.Config")
    @patch("freeipaconsistencycheck.main.FreeIPAServer")
    def test_run_exception(
        self,
        mock_freeipa_server_class,
        mock_config_class,
        mock_setup_logger,
        mock_parse_arguments,
    ):
        """Test error handling when an exception occurs during run."""
        # Set up mocks for initialization
        mock_args = MagicMock()
        mock_args.output_format = None  # Ensure we use print_table mode for the test
        mock_parse_arguments.return_value = mock_args

        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        mock_config = MagicMock()
        mock_config.domain = "example.com"
        mock_config.hosts = ["server1.example.com"]
        mock_config_class.return_value = mock_config

        mock_server = MagicMock()
        mock_freeipa_server_class.return_value = mock_server

        # Mock the ConsistencyChecker to raise an exception
        with patch(
            "freeipaconsistencycheck.main.ConsistencyChecker"
        ) as mock_checker_class:
            mock_checker = MagicMock()
            # Configure the mock to raise an exception when print_table is called
            mock_checker.print_table.side_effect = Exception("Test error")
            mock_checker_class.return_value = mock_checker

            # Create an Application instance
            app = Application()

            # Run the application - this should catch the exception
            result = app.run()

            # Verify the exception was properly handled
            mock_logger.critical.assert_called_once()
            assert "Test error" in mock_logger.critical.call_args[0][0]
            assert result == 1  # Verify the error code is returned


class TestMainFunction:
    """Tests for the main function."""

    @patch("freeipaconsistencycheck.main.Application")
    def test_successful_execution(self, mock_application_class):
        """Test successful execution of main function."""
        # Mock the Application instance
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        mock_application_class.return_value = mock_app

        # Call the main function
        result = main()

        # Verify the Application was created and run
        mock_application_class.assert_called_once()
        mock_app.run.assert_called_once()

        # Verify the return value
        assert result == 0

    @patch("freeipaconsistencycheck.main.Application")
    def test_keyboard_interrupt(self, mock_application_class):
        """Test handling of KeyboardInterrupt in main function."""
        # Mock the Application instance to raise KeyboardInterrupt
        mock_application_class.side_effect = KeyboardInterrupt()

        # Call the main function
        result = main()

        # Verify the return value indicates keyboard interrupt
        assert result == 130

    @patch("freeipaconsistencycheck.main.Application")
    def test_config_error(self, mock_application_class):
        """Test handling of ConfigError in main function."""
        # Mock the Application instance to raise ConfigError
        from freeipaconsistencycheck.utils.config import ConfigError

        mock_application_class.side_effect = ConfigError("Config error")

        # Call the main function
        result = main()

        # Verify the return value indicates configuration error
        assert result == 78

    @patch("freeipaconsistencycheck.main.Application")
    def test_value_error(self, mock_application_class):
        """Test handling of ValueError in main function."""
        # Mock the Application instance to raise ValueError
        mock_application_class.side_effect = ValueError("Value error")

        # Call the main function
        result = main()

        # Verify the return value indicates usage error
        assert result == 64

    @patch("freeipaconsistencycheck.main.Application")
    def test_general_exception(self, mock_application_class):
        """Test handling of general exceptions in main function."""
        # Mock the Application instance to raise an exception
        mock_application_class.side_effect = Exception("General error")

        # Call the main function
        result = main()

        # Verify the return value indicates error
        assert result == 1
