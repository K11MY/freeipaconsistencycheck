# FreeIPA Consistency Check (cipa) 🔍

## Overview

CheckIPA Consistency is a powerful tool originally developed by Peter Pakos, designed to verify and maintain consistency across FreeIPA servers. Initially developed in BASH and later ported to Python, this utility provides comprehensive checks for various aspects of FreeIPA deployments.

Originally created by Peter Pakos (https://github.com/peterpakos/checkipaconsistency)
This is a community-maintained fork, continuing development of the original project.

### Project History
- **Original Developer**: Peter Pakos
- **Original Repository**: [[https://github.com/peterpakos/freeipaconsistencycheck](https://github.com/peterpakos/checkipaconsistency)]
- **Initial Development**: BASH script (up to v1.3.0)
- **Python Port**: Version 2.0.0 and onwards

## Configuration

### Configuration File

By default, the tool reads its configuration from `~/.config/freeipaconsistencycheck` directory. If the config file or directory does not exist, it will be automatically created and populated with a sample configuration upon the first run.

#### Configuration File Location
- Default path: `~/.config/freeipaconsistencycheck/cipa`
- Can be overridden by setting `XDG_CONFIG_HOME` environment variable

#### Example Configuration File
```ini
[DEFAULT]
# FreeIPA domain
domain = ipa.example.com

# List of IPA servers
hosts = ipa01.example.com ipa02.example.com ipa03.example.com

# Bind DN (Directory Manager)
binddn = cn=Directory Manager

# Optional: Path to bind password file
bindpw_file = /path/to/bindpw.txt

# Nagios/Opsview plugin mode checks
nagios_checks = users,hosts,services,ugroups,hgroups,replicas

# Warning and critical thresholds
warning = 1
critical = 2
```

## Key Features

- Standalone consistency checker
- Nagios/Opsview plugin support
- Comprehensive server synchronization checks
- Flexible configuration options

## System Requirements

- FreeIPA 4.2+
- Python 3.9+
- System dependencies (detailed below)

## Installation

### Important Pre-Installation Note ⚠️

__Avoid installing with root privileges!__

Installing with root can:
- Globally install dependencies
- Potentially override existing packages
- Cause compatibility issues on FreeIPA servers

### Recommended Installation Methods

1. **User-level Install**:
   ```bash
   pip install --user freeipaconsistencycheck
   ```

2. **Virtual Environment**:
   ```bash
   python3 -m venv cipa-env
   source cipa-env/bin/activate
   pip install freeipaconsistencycheck
   ```

### System Dependency Preparation

#### Red Hat / CentOS
```bash
sudo yum install python-devel openldap-devel
```

#### Debian / Ubuntu
```bash
sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev
```

## Docker Container Support

### Building the Container

1. Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsasl2-dev \
    python3-dev \
    libldap2-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .

ENTRYPOINT ["cipa"]
CMD ["--help"]
```

2. Build the image:
```bash
docker build -t freeipaconsistencycheck .
```

### Running the Container

#### Basic Usage
```bash
# Display help
docker run --rm freeipaconsistencycheck

# Check specific domain
docker run --rm freeipaconsistencycheck -d ipa.example.com -W your_bind_password
```

#### Mounting Configuration

You can mount your configuration file or directory to the container:

1. **Mount Specific Configuration File**:
```bash
docker run --rm \
    -v /path/to/your/cipa:/root/.config/freeipaconsistencycheck/cipa \
    freeipaconsistencycheck
```

2. **Mount Entire Configuration Directory**:
```bash
docker run --rm \
    -v /path/to/your/freeipaconsistencycheck:/root/.config/cipa \
    freeipaconsistencycheck
```

3. **Additional Container Run Options**:
```bash
docker run --rm \
    -v /path/to/your/cipa:/root/.config/freeipaconsistencycheck/cipa \
    -v /path/to/bindpw.txt:/bindpw.txt \
    freeipaconsistencycheck
```

## Command-Line Usage

```
$ cipa --help
usage: cipa [-H [HOSTS [HOSTS ...]]] [-d [DOMAIN]] [-D [BINDDN]] [-W [BINDPW]]
            [--help] [--version] [--debug] [--verbose] [--quiet]
            [-l [LOG_FILE]] [--no-header] [--no-border]
            [-n [{,all,users,susers,pusers,hosts,services,ugroups,hgroups,ngroups,hbac,sudo,zones,certs,conflicts,ghosts,bind,msdcs,replicas}]]
            [-w WARNING] [-c CRITICAL]
            [-o [{json,yaml}]]
```

### Key Options

| Option | Description | Default |
|--------|-------------|---------|
| `-H`, `--hosts` | List of IPA servers | None |
| `-d`, `--domain` | IPA domain | None |
| `--debug` | Enable debug mode | False |
| `--verbose` | Increase output verbosity | False |
| `-w`, `--warning` | Threshold for warning | 1 |

## Example Output

Here's a comprehensive example of the tool's output when checking a multi-server FreeIPA deployment:

```
$ cipa -d ipa.example.com -W ********
+--------------------+----------+----------+----------+-----------+----------+----------+-------+
| FreeIPA servers:   | ipa01    | ipa02    | ipa03    | ipa04     | ipa05    | ipa06    | STATE |
+--------------------+----------+----------+----------+-----------+----------+----------+-------+
| Active Users       | 1199     | 1199     | 1199     | 1199      | 1199     | 1199     | OK    |
| Stage Users        | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
| Preserved Users    | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
| Hosts              | 357      | 357      | 357      | 357       | 357      | 357      | OK    |
| Services           | 49       | 49       | 49       | 49        | 49       | 49       | OK    |
| User Groups        | 55       | 55       | 55       | 55        | 55       | 55       | OK    |
| Host Groups        | 29       | 29       | 29       | 29        | 29       | 29       | OK    |
| Netgroups          | 11       | 11       | 11       | 11        | 11       | 11       | OK    |
| HBAC Rules         | 3        | 3        | 3        | 3         | 3        | 3        | OK    |
| SUDO Rules         | 2        | 2        | 2        | 2         | 2        | 2        | OK    |
| DNS Zones          | 114      | 114      | 114      | 114       | 114      | 114      | OK    |
| Certificates       | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
| LDAP Conflicts     | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
| Ghost Replicas     | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
| Anonymous BIND     | ON       | ON       | ON       | ON        | ON       | ON       | OK    |
| Microsoft ADTrust  | False    | False    | False    | False     | False    | False    | OK    |
| Replication Status | ipa03 0  | ipa03 0  | ipa04 0  | ipa03 0   | ipa03 0  | ipa04 0  | OK    |
|                    | ipa04 0  | ipa04 0  | ipa05 0  | ipa01 0   | ipa01 0  |          |       |
|                    | ipa05 0  | ipa05 0  | ipa01 0  | ipa02 0   | ipa02 0  |          |       |
|                    | ipa02 0  | ipa01 0  | ipa02 0  | ipa06 0   |          |          |       |
+--------------------+----------+----------+----------+-----------+----------+----------+-------+
```

## Debugging

For troubleshooting:

```bash
# Basic debug mode
cipa --debug

# Verbose debugging
cipa --debug --verbose
```

## LDAP Conflicts

Most replication conflicts are automatically resolved, with the most recent change taking precedence. In rare cases, manual intervention may be required.

When LDAP conflicts are detected:
1. Identify conflicting entries
2. Determine which entries to preserve or delete

For detailed guidance, refer to the [Red Hat Directory Server Administration Guide](https://access.redhat.com/documentation/en-us/red_hat_directory_server/10/html/administration_guide/managing_replication-solving_common_replication_conflicts).

## Contributing

We welcome contributions! If you find any issues or have suggestions for improvement:
- Open an issue on the project repository
- Submit pull requests
- Provide detailed information about your proposed changes

## License

GNU GENERAL PUBLIC LICENSE Version 3

## Contact

For support or inquiries, please open an issue on the project's GitHub repository or contact the original developer, Peter Pakos.