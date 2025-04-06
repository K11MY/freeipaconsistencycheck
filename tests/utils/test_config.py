"""
Test Suite for Configuration Module

This module provides detailed unit tests for the freeipaconsistencycheck configuration
handling utilities. It thoroughly tests various configuration-related functions,
including configuration file path generation, default configuration creation,
configuration loading, and validation.

Key Testing Objectives:
- Validate configuration file path generation
- Test default configuration creation
- Verify configuration loading from files
- Validate configuration parameter handling
- Check command-line argument overrides
- Ensure robust error handling and validation

Test Coverage:
- Configuration file path generation
- Default configuration creation
- Configuration file parsing
- Configuration validation
- Command-line argument processing
"""

import pytest
import os
from unittest.mock import patch, mock_open, MagicMock


@pytest.fixture
def mock_file_system():
    """Fixture to mock file system operations for both pathlib and os.path."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("os.path.exists", return_value=True),
    ):
        yield


@pytest.fixture
def mock_file_read(request):
    """Fixture to mock file reading operations with configurable content."""
    content = getattr(
        request,
        "param",
        "[IPA]\nDOMAIN = test.example.com\nHOSTS = server1, server2\nBINDDN = cn=Admin\nBINDPW = secret123",
    )

    with (
        patch("pathlib.Path.read_text", return_value=content),
        patch("builtins.open", mock_open(read_data=content)),
    ):
        yield


@pytest.fixture
def mock_config_parser():
    """Fixture to mock ConfigParser behavior."""
    with (
        patch("configparser.ConfigParser.read"),
        patch("configparser.ConfigParser.has_section", return_value=True),
        patch("configparser.ConfigParser.has_option", return_value=True),
        patch("configparser.ConfigParser.get") as mock_get,
    ):
        # Default config values
        def get_side_effect(section, option):
            values = {
                "DOMAIN": "test.example.com",
                "HOSTS": "server1, server2",
                "BINDDN": "cn=Admin",
                "BINDPW": "secret123",
            }
            return values.get(option, "")

        mock_get.side_effect = get_side_effect
        yield mock_get


@pytest.fixture
def mock_cli_config_parser():
    """Fixture to mock ConfigParser behavior with file values for CLI override tests."""
    with (
        patch("configparser.ConfigParser.read"),
        patch("configparser.ConfigParser.has_section", return_value=True),
        patch("configparser.ConfigParser.has_option", return_value=True),
        patch("configparser.ConfigParser.get") as mock_get,
    ):
        # File config values that should be overridden by CLI args
        def get_side_effect(section, option):
            values = {
                "DOMAIN": "file.example.com",
                "HOSTS": "file1, file2",
                "BINDDN": "cn=FileAdmin",
                "BINDPW": "filesecret",
            }
            return values.get(option, "")

        mock_get.side_effect = get_side_effect
        yield


from freeipaconsistencycheck.utils.config import (
    Config,
    ConfigError,
    get_config_file_path,
    create_default_config,
    load_config,
    validate_config,
)


class TestConfigFilePath:
    """Tests for the get_config_file_path function."""

    def test_with_xdg_config_home(self):
        """Test path generation when XDG_CONFIG_HOME is set."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom/config/path"}):
            path = get_config_file_path("myapp")
            # Convert Path to string for comparison if needed
            if hasattr(path, "__fspath__"):  # Check if it's a Path-like object
                path_str = str(path)
            else:
                path_str = path
            assert path_str == os.path.join(
                "/custom/config/path", "freeipaconsistencycheck", "myapp"
            )

    def test_default_location(self):
        """Test default path when XDG_CONFIG_HOME is not set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.path.expanduser", return_value="/home/user"):
                path = get_config_file_path("myapp")
                # Convert Path to string for comparison if needed
                if hasattr(path, "__fspath__"):  # Check if it's a Path-like object
                    path_str = str(path)
                else:
                    path_str = path
                assert path_str == os.path.join(
                    "/home/user", ".config", "freeipaconsistencycheck", "myapp"
                )


class TestCreateDefaultConfig:
    """Tests for the create_default_config function."""

    @pytest.fixture
    def mock_directory_creation(self):
        """Fixture to mock directory creation for both pathlib and os."""
        with (
            patch("pathlib.Path.mkdir", autospec=True) as mock_path_mkdir,
            patch("os.makedirs") as mock_makedirs,
            patch(
                "pathlib.Path.parent", create=True, new_callable=MagicMock
            ) as mock_parent,
        ):

            # Configure mock_parent to return a Path object with mkdir method
            parent_mock = MagicMock()
            parent_mock.mkdir = mock_path_mkdir
            mock_parent.__get__ = MagicMock(return_value=parent_mock)

            yield {"path_mkdir": mock_path_mkdir, "os_makedirs": mock_makedirs}

    def test_create_default_config(self, mock_logger, mock_directory_creation):
        """Test creating a default configuration file."""
        # Mock file operations
        m = mock_open()
        config_file = os.path.join("/tmp", "config")

        with patch("builtins.open", m):
            create_default_config(config_file, mock_logger)

            # Check that either pathlib or os.makedirs was used
            directory_created = (
                mock_directory_creation["os_makedirs"].called
                or mock_directory_creation["path_mkdir"].called
            )
            assert (
                directory_created
            ), "Directory was not created with either pathlib or os.makedirs"

            # Verify the file was written with default values
            m.assert_called_once_with(str(config_file), "w")

            # Check that the ConfigParser.write method was called
            handle = m()
            assert handle.write.called

            # Verify the logger was used
            mock_logger.info.assert_called_once()


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_file_not_exists(self, mock_logger):
        """Test behavior when config file doesn't exist."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("os.path.exists", return_value=False),
            patch(
                "freeipaconsistencycheck.utils.config.create_default_config"
            ) as mock_create,
        ):

            result = load_config("myapp", mock_logger)

            # Verify create_default_config was called
            mock_create.assert_called_once()

            # Check the returned values
            domain, hosts, binddn, bindpw = result
            assert domain is None
            assert hosts == []
            assert binddn == "cn=Directory Manager"
            assert bindpw is None

    def test_load_config_from_file(
        self, mock_logger, mock_file_system, mock_file_read, mock_config_parser
    ):
        """Test loading configuration from a file."""
        # Call the function with mocked environment
        domain, hosts, binddn, bindpw = load_config("myapp", mock_logger)

        # Verify the returned values
        assert domain == "test.example.com"
        assert hosts == ["server1", "server2"]
        assert binddn == "cn=Admin"
        assert bindpw == "secret123"

    def test_command_line_overrides(
        self, mock_logger, mock_file_system, mock_file_read, mock_cli_config_parser
    ):
        """Test that command-line arguments override file configuration."""
        # Call with command-line overrides
        domain, hosts, binddn, bindpw = load_config(
            "myapp",
            mock_logger,
            domain_arg="cli.example.com",
            hosts_arg=["cli1", "cli2"],
            binddn_arg="cn=CLIAdmin",
            bindpw_arg="clisecret",
        )

        # Verify the command-line values were used
        assert domain == "cli.example.com"
        assert hosts == ["cli1", "cli2"]
        assert binddn == "cn=CLIAdmin"
        assert bindpw == "clisecret"


class TestValidateConfig:
    """Tests for the validate_config function."""

    def test_valid_config(self, mock_logger):
        """Test validation with a valid configuration."""
        # This should not raise any exceptions
        validate_config(
            domain="example.com",
            hosts=["server1.example.com", "server2.example.com"],
            binddn="cn=Admin",
            bindpw="secret",
            log=mock_logger,
        )

    def test_missing_domain(self, mock_logger):
        """Test validation with a missing domain."""
        with pytest.raises(ConfigError) as excinfo:
            validate_config(
                domain=None,
                hosts=["server1.example.com"],
                binddn="cn=Admin",
                bindpw="secret",
                log=mock_logger,
            )
        assert "domain not set" in str(excinfo.value).lower()

    def test_invalid_hostname(self, mock_logger):
        """Test validation with an invalid hostname."""
        with pytest.raises(ConfigError) as excinfo:
            validate_config(
                domain="example.com",
                hosts=["server1.example.com", "invalid server"],  # Space in hostname
                binddn="cn=Admin",
                bindpw="secret",
                log=mock_logger,
            )
        assert "incorrect server name" in str(excinfo.value).lower()

    def test_missing_binddn(self, mock_logger):
        """Test validation with a missing binddn."""
        with pytest.raises(ConfigError) as excinfo:
            validate_config(
                domain="example.com",
                hosts=["server1.example.com"],
                binddn=None,
                bindpw="secret",
                log=mock_logger,
            )
        assert "bind dn not set" in str(excinfo.value).lower()

    def test_missing_bindpw(self, mock_logger):
        """Test validation with a missing bindpw."""
        with pytest.raises(ConfigError) as excinfo:
            validate_config(
                domain="example.com",
                hosts=["server1.example.com"],
                binddn="cn=Admin",
                bindpw=None,
                log=mock_logger,
            )
        assert "bind password not set" in str(excinfo.value).lower()


class TestConfigClass:
    """Tests for the Config class."""

    def test_init_success(self, mock_logger):
        """Test successful initialization of Config class."""
        with patch("freeipaconsistencycheck.utils.config.load_config") as mock_load:
            with patch(
                "freeipaconsistencycheck.utils.config.validate_config"
            ) as mock_validate:
                # Configure load_config to return valid values
                mock_load.return_value = (
                    "example.com",
                    ["server1", "server2"],
                    "cn=Admin",
                    "secret",
                )

                # Create a Config instance
                config = Config("myapp", mock_logger)

                # Verify that load_config and validate_config were called
                mock_load.assert_called_once()
                mock_validate.assert_called_once()

                # Verify the attributes were set correctly
                assert config.domain == "example.com"
                assert config.hosts == ["server1", "server2"]
                assert config.binddn == "cn=Admin"
                assert config.bindpw == "secret"

    def test_init_with_args(self, mock_logger):
        """Test initialization with command-line arguments."""
        with patch("freeipaconsistencycheck.utils.config.load_config") as mock_load:
            with patch("freeipaconsistencycheck.utils.config.validate_config"):
                # Configure load_config to return some values
                mock_load.return_value = (
                    "example.com",
                    ["server1", "server2"],
                    "cn=Admin",
                    "secret",
                )

                # Create a Config instance with command-line arguments
                config = Config(
                    "myapp",
                    mock_logger,
                    domain_arg="cli.example.com",
                    hosts_arg=["cli1", "cli2"],
                    binddn_arg="cn=CLIAdmin",
                    bindpw_arg="clisecret",
                )

                # Verify that load_config was called
                mock_load.assert_called_once()

                # Check that the call had the right arguments without requiring exact parameter names
                call_args = mock_load.call_args[0]
                assert call_args[0] == "myapp"
                assert call_args[1] == mock_logger

                # Check the kwargs or positional args that follow
                remaining_args = mock_load.call_args[0][2:] + tuple(
                    mock_load.call_args[1].values()
                )
                assert "cli.example.com" in remaining_args
                assert ["cli1", "cli2"] in remaining_args
                assert "cn=CLIAdmin" in remaining_args
                assert "clisecret" in remaining_args

    def test_validation_failure(self, mock_logger):
        """Test handling of validation failure."""
        with patch("freeipaconsistencycheck.utils.config.load_config") as mock_load:
            with patch(
                "freeipaconsistencycheck.utils.config.validate_config"
            ) as mock_validate:
                # Configure load_config to return some values
                mock_load.return_value = ("example.com", [], "cn=Admin", "secret")

                # Configure validate_config to raise an exception
                mock_validate.side_effect = ConfigError("No hosts specified")

                # Attempt to create a Config instance, which should raise the exception
                with pytest.raises(ConfigError) as excinfo:
                    Config("myapp", mock_logger)

                assert "No hosts specified" in str(excinfo.value)

    def test_as_dict(self, mock_logger):
        """Test the as_dict method."""
        with patch("freeipaconsistencycheck.utils.config.load_config") as mock_load:
            with patch("freeipaconsistencycheck.utils.config.validate_config"):
                # Configure load_config to return valid values
                mock_load.return_value = (
                    "example.com",
                    ["server1", "server2"],
                    "cn=Admin",
                    "secret",
                )

                # Create a Config instance
                config = Config("myapp", mock_logger)

                # Test the as_dict method
                config_dict = config.as_dict()

                # Verify the dictionary contains the correct values
                assert config_dict["domain"] == "example.com"
                assert config_dict["hosts"] == ["server1", "server2"]
                assert config_dict["binddn"] == "cn=Admin"
                assert config_dict["bindpw"] == "secret"

    def test_get_host_domains(self, mock_logger):
        """Test the get_host_domains method."""
        with patch("freeipaconsistencycheck.utils.config.load_config") as mock_load:
            with patch("freeipaconsistencycheck.utils.config.validate_config"):
                # Configure load_config to return valid values
                mock_load.return_value = (
                    "example.com",
                    ["server1", "server2", "server3.example.com"],
                    "cn=Admin",
                    "secret",
                )

                # Create a Config instance
                config = Config("myapp", mock_logger)

                # Test the get_host_domains method
                host_domains = config.get_host_domains()

                # Verify the method returns fully qualified domain names
                assert host_domains == [
                    "server1.example.com",
                    "server2.example.com",
                    "server3.example.com",
                ]
