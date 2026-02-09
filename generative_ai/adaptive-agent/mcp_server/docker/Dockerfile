# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# User configuration
ARG UID=1000
ARG GID=1000
ARG UNAME=appuser

# Dockerfile for DataRobot MCP Custom Model Execution Environment
FROM datarobot/mirror_chainguard_datarobot.com_python-fips:3.12-dev AS base

ARG UID
ARG GID
ARG UNAME

USER root

# Create group and user
RUN addgroup -g "$GID" "$UNAME" && \
    adduser -D -u "$UID" -G "$UNAME" -s /bin/bash "$UNAME"

# Set working directory
WORKDIR /opt/code
ENV HOME=/opt/code

# Install system dependencies using apk
# hadolint ignore=DL3018
RUN apk add --no-cache \
    build-base \
    curl \
    bash

# Copy requirements and wheels
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (Pulumi copies mcp files to the build context)
COPY . .

# Make start_server.sh executable and set ownership
RUN chown -R $UNAME:$UNAME /opt/code \
    && chmod +x start_server.sh

# Switch to non-root user
USER $UNAME

# Expose port (adjust if your app uses a different port)
EXPOSE 8080

# Set the default command
CMD ["sh", "/opt/code/start_server.sh"]
