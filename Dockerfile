# PYTHON VERSION
ARG PYTHON_VERSION=3.9
# Build stage
FROM python:${PYTHON_VERSION}-slim AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libkrb5-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the files needed for installation
COPY pyproject.toml ./
COPY src/ ./src/

# Build the wheel package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    ls -la dist/

# Final stage
FROM python:${PYTHON_VERSION}-slim
LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="FreeIPA consistency checker"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libkrb5-dev \
    krb5-user \
    ldap-utils \
    gcc \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user
RUN groupadd -r cipauser && \
    useradd -r -g cipauser -m -d /home/cipauser cipauser && \
    mkdir -p /home/cipauser/.config && \
    chown -R cipauser:cipauser /home/cipauser

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the built wheel from the builder stage
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Give cipauser access to the virtual environment
RUN chown -R cipauser:cipauser /opt/venv

# Switch to non-root user
USER cipauser
WORKDIR /home/cipauser

# Set HOME for the non-root user
ENV HOME=/home/cipauser

# Set the entrypoint
ENTRYPOINT ["cipa"]
