# Development Guide

This guide provides comprehensive instructions for setting up, developing, and deploying the DataRobot MCP (Model Context Protocol) Server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Running the Server](#running-the-server)
- [Development Workflow](#development-workflow)
  - [MCP Client Configuration](#mcp-client-configuration)
  - [OpenTelemetry Configuration](#opentelemetry-configuration)
  - [Dynamic Tool Registration](#dynamic-tool-registration)
  - [Dynamic Prompt Registration](#dynamic-prompt-registration)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Debugging](#debugging)

## Prerequisites

Before you begin, ensure you have the following:

- **uv**: Python package installer and project manager
- **DataRobot Account**: Active DataRobot account with API credentials
- **Python 3.11+**: Required Python version

## Initial Setup

### 1. Install uv

If you haven't already installed `uv`, run the following command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For alternative installation methods, refer to the [uv documentation](https://github.com/astral-sh/uv).

### 2. Configure Environment Variables

Create a `.env` file in the root directory. You can copy from `.env.template` located in the app directory.

Then configure the following variables:

#### Required Variables

```bash
# DataRobot API credentials
DATAROBOT_API_TOKEN=your_api_token
DATAROBOT_ENDPOINT=your_datarobot_endpoint
```

#### Optional Variables

```bash
# MCP Server Configuration
# MCP_SERVER_NAME=your_server_name
# MCP_SERVER_PORT=8080
# MCP_SERVER_LOG_LEVEL=DEBUG

# Dynamic Tool Registration
# MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP=true
# MCP_SERVER_TOOL_REGISTRATION_ALLOW_EMPTY_SCHEMA=true
# MCP_SERVER_TOOL_REGISTRATION_DUPLICATE_BEHAVIOR=warn

# Dynamic Prompt Registration
# MCP_SERVER_REGISTER_DYNAMIC_PROMPTS_ON_STARTUP=true
# MCP_SERVER_PROMPT_REGISTRATION_DUPLICATE_BEHAVIOR=warn

# Application Configuration
# APP_LOG_LEVEL=DEBUG

# OpenTelemetry Configuration
# OTEL_ENABLED=false
# OTEL_ENABLED_HTTP_INSTRUMENTORS=true
```

## Running the Server

### Local Development

To start the MCP server locally for development:

```bash
task mcp:dev
```

This command will:
- Create a virtual environment (if needed)
- Install all dependencies
- Start the MCP server on the configured port (default: 8080)

### Deployment to DataRobot

To deploy the MCP server to DataRobot:

```bash
task deploy
```

This will build and deploy the server as a DataRobot custom model application.

## Development Workflow

### MCP Client Configuration

To use the MCP server with AI assistants, configure your MCP client to connect to the server.

#### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "datarobot-mcp-server": {
      "url": "http://localhost:8080/mcp/"
    },
    "datarobot-mcp-server-remote": {
      "url": "https://app.datarobot.com/deployments/<deployment-id>/directAccess/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY",
        "x-datarobot-api-key": "YOUR_API_KEY"
      }
    }
  }
}
```

#### Visual Studio Code

Edit `~/Library/Application Support/Code/User/mcp.json` (macOS) or `%APPDATA%\Code\User\mcp.json` (Windows):

```json
{
  "mcp": {
    "servers": {
      "datarobot-mcp-server": {
        "url": "http://localhost:8080/mcp/",
        "type": "http"
      }
    }
  }
}
```

#### Claude Desktop

1. Install Node.js (required for the MCP remote client):

```bash
brew install node
```

2. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "datarobot-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://app.datarobot.com/deployments/<deployment-id>/directAccess/mcp/",
        "--header",
        "Authorization: ${AUTH_HEADER}",
        "--transport",
        "http"
      ],
      "env": {
        "AUTH_HEADER": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

For more detailed client setup instructions, see the [MCP Client Setup Guide](docs/mcp_client_setup.md).

### OpenTelemetry Configuration

The server supports OpenTelemetry for distributed tracing and observability.

#### Features

- **Automatic HTTP Client Instrumentation**: Supports aiohttp, httpx, and requests
- **Tool Execution Tracing**: Captures tool parameters and results
- **Error Tracking**: Monitors errors and status
- **Custom Attributes**: Support for custom tracing attributes

#### Configuration

Add the following environment variables to your `.env` file:

```bash
# Enable/disable OpenTelemetry (default: true)
OTEL_ENABLED=true
# Enable/disable HTTP instrumentors (default: false)
OTEL_ENABLED_HTTP_INSTRUMENTORS=false
```

### Dynamic Tool Registration

The server can automatically discover and register DataRobot deployments as MCP tools.

When enabled, the server scans for deployments tagged with `tool` and registers each as an MCP tool automatically. This allows you to expose DataRobot models as tools without manual configuration.

For detailed information about this feature, including supported workflows and prerequisites, refer to the [Dynamic Tool Registration Guide](docs/dynamic_tool_registration.md).

#### Configuration

```bash
# Enable/disable Dynamic Tool Registration on startup (default: false)
MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP=true

# Allow tools with empty schemas (default: false)
MCP_SERVER_TOOL_REGISTRATION_ALLOW_EMPTY_SCHEMA=true

# Behavior when duplicate tools are found: 'error', 'warn', or 'ignore' (default: 'warn')
MCP_SERVER_TOOL_REGISTRATION_DUPLICATE_BEHAVIOR=warn
```

### Dynamic Prompt Registration

The server can automatically discover and register DataRobot prompts as MCP prompts.

#### Configuration

```bash
# Enable/disable Dynamic Prompt Registration on startup (default: false)
MCP_SERVER_REGISTER_DYNAMIC_PROMPTS_ON_STARTUP=true

# Behavior when duplicate prompts are found: 'error', 'warn', or 'ignore' (default: 'warn')
MCP_SERVER_PROMPT_REGISTRATION_DUPLICATE_BEHAVIOR=warn
```

## Code Quality

Maintain code quality by running linting and formatting checks:

```bash
# Install dependencies and run linting/formatting
uv sync --all-extras && uv run ruff check --select I --fix && uv run ruff format
```

This command will:
- Install all dependencies including development extras
- Check import sorting and fix issues
- Format code according to project standards

## Testing

Run the test suite:

```bash
# Install dependencies and run tests
uv sync --all-extras && uv run pytest
```

For more testing options, see the project's test documentation or run:

```bash
# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/unit/test_user_tools.py

# Run tests with verbose output
uv run pytest -v
```

## Debugging

### Viewing Logs

Monitor the MCP server logs to debug issues:

- **Local Development**: Logs are output to the console where you ran `task mcp:dev`
- **Deployed Server**: Check the DataRobot deployment logs in the DataRobot UI

### Common Issues

1. **Connection Errors**: Verify the server is running and the URL is correct
2. **Authentication Failures**: Check that your `DATAROBOT_API_TOKEN` is valid
3. **Tool Registration Issues**: Review the server logs for registration errors
4. **Port Conflicts**: Ensure the configured port (default: 8080) is available

### Debug Mode

Enable debug logging by setting:

```bash
MCP_SERVER_LOG_LEVEL=DEBUG
APP_LOG_LEVEL=DEBUG
```

This will provide detailed logging output for troubleshooting.
