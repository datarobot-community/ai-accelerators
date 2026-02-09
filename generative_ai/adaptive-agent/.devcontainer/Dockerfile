# Base Python devcontainer
FROM mcr.microsoft.com/devcontainers/python:3.12

# Until we have a mirror for GitHub releases, we can't use the latest versions
# https://datarobot.atlassian.net/browse/CFX-4255
ENV PULUMI_DATAROBOT_PLUGIN_VERSION=v0.10.27
ENV DR_VERSION=0.2.24

# Install GDB to enable PyCharm -> Attach to Process...
RUN apt update && apt install -y gdb

USER vscode

ENV PATH="/home/vscode/.local/bin:${PATH}"

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install pre-commit

# Install Task (Taskfile runner)
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /home/vscode/.local/bin

# Install Pulumi
RUN curl -fsSL https://get.pulumi.com | sh -s -- --install-root "/home/vscode/.local" && \
    pulumi plugin install resource datarobot ${PULUMI_DATAROBOT_PLUGIN_VERSION} --server https://github.com/datarobot-community/pulumi-datarobot/releases/download/${PULUMI_DATAROBOT_PLUGIN_VERSION}/

ENV PULUMI_SKIP_UPDATE_CHECK=true

# Install dr CLI
RUN curl -L -o /tmp/dr.tar.gz \
    https://github.com/datarobot-oss/cli/releases/download/v${DR_VERSION}/dr_v${DR_VERSION}_Linux_x86_64.tar.gz \
    && tar -xzf /tmp/dr.tar.gz -C ~/.local/bin dr \
    && chmod +x ~/.local/bin/dr \
    && rm /tmp/dr.tar.gz

# Verify installations
RUN python --version && uv --version && task --version && pulumi version && dr --version && \
    pulumi login --local

ENV SHELL=/bin/bash

# Set working directory
WORKDIR /workspace
