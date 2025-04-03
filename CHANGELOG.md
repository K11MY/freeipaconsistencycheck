# Changelog

## [3.0.0] - 2025-04-06

### Added
- Docker container support with `Dockerfile`
- GitHub Actions for CI/CD
- JSON and YAML output formats

### Changed
- Minimum Python version upgraded to 3.9+
- Removed Travis CI configuration
- Removed Nagios plugin support
- Rename project to freeipaconsistencycheck

### Removed
- Legacy Nagios plugin mode
- Support for older Python versions (below 3.9)
- Travis CI configuration

### Improved
- Project structure updated for modern Python packaging
- Simplified configuration management
- Enhanced output format options with JSON and YAML support

### Migration Notes
- Requires Python 3.9 or higher
- Nagios plugin functionality has been removed
- New output formats (JSON/YAML) provide alternative reporting methods