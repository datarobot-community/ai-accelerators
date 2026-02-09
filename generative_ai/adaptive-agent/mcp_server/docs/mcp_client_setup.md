# MCP client setup

This guide covers how to configure various MCP clients (e.g., Cursor, VSCode, Claude Desktop, etc.) to connect to your DataRobot MCP server, both locally and when deployed to DataRobot.

The guide covers:

- **Configuring Cursor, VSCode, and Claude Desktop**
- **Both local development and production setups**
- **Authentication with DataRobot API tokens**
- **Troubleshooting common connection issues**
- **Setting up multiple environments**

## Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
  - [Cursor](#cursor)
  - [VSCode](#vscode)
  - [Claude Desktop](#claude-desktop)
- [Verifying the connection](#verifying-the-connection)
- [Troubleshooting decision tree](#troubleshooting-decision-tree)
- [Advanced features (optional)](#advanced-features-optional)
- [Additional resources](#additional-resources)

## Prerequisites

This guide assumes you already have:

- A [running MCP server](../README.md#getting-started) (locally or deployed to DataRobot)
- Your [DataRobot API token](../README.md#api-keys) (for remote connections)
- The [MCP endpoint URL](../README.md#mcp-endpoint)

# Quick start

The sections below provide a quick start guide for configuring your MCP client to connect to your local or deployed DataRobot MCP server.
In the steps provided, replace `[YOUR_DATA_ROBOT_ENDPOINT]` with your actual DataRobot endpoint, and `[YOUR_DATA_ROBOT_API_KEY]` with your actual DataRobot API key.
See [DataRobot API keys](../README.md#api-keys) or [DataRobot API keys documentation](https://docs.datarobot.com/en/docs/get-started/acct-mgmt/acct-settings/api-key-mgmt.html) for more information.

## Cursor

Edit `~/.cursor/mcp.json` and add the following configuration:

### Local MCP server

```json
{
  "mcpServers": {
    "datarobot-local": {
      "url": "http://localhost:8080/mcp/"
    }
  }
}
```

### MCP server deployed to DataRobot

```json
{
  "mcpServers": {
    "datarobot-production": {
      "url": "https://[YOUR_DATA_ROBOT_ENDPOINT]/deployments/[YOUR_DEPLOYMENT_ID]/directAccess/mcp/",
      "headers": {
        "Authorization": "Bearer [YOUR_DATA_ROBOT_API_KEY]"
      }
    }
  }
}
```

**After updating configuration:**

1. Restart Cursor.
2. Test: Ask Cursor "What MCP tools are available?"

## VSCode

Edit `~/Library/Application Support/Code/User/mcp.json` (macOS) or the equivalent location on your OS:

### Local MCP server

```json
{
  "mcp": {
    "servers": {
      "datarobot-local": {
        "url": "http://localhost:8080/mcp/",
        "type": "http"
      }
    }
  }
}
```

### MCP server deployed to DataRobot

```json
{
  "mcp": {
    "servers": {
      "datarobot-production": {
        "url": "https://[YOUR_DATA_ROBOT_ENDPOINT]/deployments/[YOUR_DEPLOYMENT_ID]/directAccess/mcp/",
        "type": "http",
        "headers": {
          "Authorization": "Bearer [YOUR_DATA_ROBOT_API_KEY]"
        }
      }
    }
  }
}
```

**After updating configuration:**

1. Restart VSCode or reload window (`Cmd+Shift+P` → "Developer: Reload Window").
2. Test: Check Output panel → Select "MCP" from dropdown for connection status

## Claude Desktop

> **Note**: Claude Desktop requires Node.js to use the `mcp-remote` proxy for HTTP-based MCP servers.

1. Install Node.js (if not already installed):

```bash
# macOS
brew install node

# Or download from https://nodejs.org/
```

2. Edit configuration file: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent on your OS.

### Local MCP server

```json
{
  "mcpServers": {
    "datarobot-local": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://localhost:8080/mcp/",
        "--transport",
        "http"
      ]
    }
  }
}
```

### MCP server deployed to DataRobot

```json
{
  "mcpServers": {
    "datarobot-production": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://[YOUR_DATA_ROBOT_ENDPOINT]/deployments/[YOUR_DEPLOYMENT_ID]/directAccess/mcp/",
        "--header",
        "Authorization: ${AUTH_HEADER}",
        "--transport",
        "http"
      ],
      "env": {
        "AUTH_HEADER": "Bearer [YOUR_DATA_ROBOT_API_KEY]"
      }
    }
  }
}
```

**After updating configuration:**

1. Completely quit Claude Desktop (not just close the window) and restart it.
2. Test: Ask Claude "What tools do you have access to?"

## Multiple environments (optional)

You can configure multiple MCP servers (e.g., local, staging, production) in the same client configuration. This is useful for testing changes locally before deploying.

*Example for Cursor*:

```json
{
  "mcpServers": {
    "local": {
      "url": "http://localhost:8080/mcp/"
    },
    "production": {
      "url": "https://[YOUR_DATA_ROBOT_ENDPOINT]/deployments/[YOUR_DEPLOYMENT_ID]/directAccess/mcp/",
      "headers": {
        "Authorization": "Bearer [YOUR_DATA_ROBOT_API_KEY]"
      }
    }
  }
}
```

Your client will connect to all configured servers and make their tools available.

## Verifying the connection

After configuring your client, use these interactive tests to verify everything works:

### Server verification

1. **Verify that the server is running**:

   ```bash
   curl http://localhost:8080/
   ```
  
  Expected output: `{"status": "healthy", "message": "DataRobot MCP Server is running"}`

2. **Check MCP Endpoint**:

   ```bash
   curl http://localhost:8080/mcp/
   ```

  Expected output: MCP protocol information (JSON response)

### Client-specific verification

#### Cursor verification

1. **Open Cursor**
2. **Open Command Palette**: `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
3. **Type "MCP"** - you should see MCP-related commands
4. **Test with AI**: Ask "What MCP tools are available?" or "List all available tools"
5. **Expected result**: AI should list DataRobot tools
   ✅ **Cursor MCP connection working**

#### VSCode verification

1. **Open VSCode**
2. **Open Output Panel**: `View → Output`
3. **Select "MCP" from dropdown** (if available)
4. **Look for connection messages**: Should show successful MCP server connection
5. **Test with AI**: Use AI features and ask about available tools
   ✅ **VSCode MCP connection working**

#### Claude Desktop verification

1. **Open Claude Desktop**
2. **Check logs**: `~/Library/Logs/Claude/mcp*.log` (macOS) or equivalent on your OS
3. **Look for**: "Connected to MCP server" or similar success messages
4. **Test with Claude**: Ask "What tools do you have access to?"
5. **Expected result**: Claude should mention DataRobot tools
   ✅ **Claude Desktop MCP connection working**

### Troubleshooting failed connections

**If verification fails:**

3. **Check Client Logs**:
   - **Cursor**: View → Output → Select "MCP Logs"
   - **Claude Desktop**: Check `~/Library/Logs/Claude/mcp*.log`
   - **VSCode**: View → Output → Select MCP-related output

## Troubleshooting decision tree

Use this decision tree to quickly diagnose and fix common issues:

### Server issues

**Server won't start?**

```
├── Port 8080 in use?
│   ├── Yes → Kill process: `lsof -i :8080 | xargs kill -9`
│   └── No → Check dependencies: `task install`
├── Missing dependencies?
│   ├── Yes → Run: `task install`
│   └── No → Check environment variables
└── Invalid API token?
    ├── Yes → Verify token in DataRobot UI → Account Settings → API Tokens
    └── No → Check .env file format
```

**Server starts but returns errors?**

```
├── Check server logs for specific error messages
├── Verify DATAROBOT_API_TOKEN is valid
├── Check DATAROBOT_ENDPOINT URL format
└── Ensure required environment variables are set
```

### Client connection issues

**Client can't connect to server?**

```
├── Server running?
│   ├── No → Start server: `task dev`
│   └── Yes → Check URL in client config
├── Wrong URL in config?
│   ├── Local: Should be `http://localhost:8080/mcp/`
│   └── Remote: Should be `https://app.datarobot.com/deployments/<id>/directAccess/mcp/`
├── Firewall blocking?
│   ├── Check local firewall settings
│   └── Check corporate network restrictions
└── Client needs restart?
    ├── Cursor: Completely quit and restart
    ├── VSCode: Reload window (Cmd+Shift+P → "Developer: Reload Window")
    └── Claude Desktop: Completely quit and restart
```

**Tools not showing up in client?**

```
├── Server logs show tool registration errors?
│   ├── Yes → Check tool docstrings and type hints
│   └── No → Check client configuration
├── Client needs restart after server changes?
│   ├── Yes → Restart client application
│   └── No → Check MCP endpoint URL
└── Wrong endpoint URL?
    ├── Verify URL format and deployment ID
    └── Test endpoint directly: `curl <mcp-endpoint-url>`
```

### Authentication issues (remote)

**Authentication errors with remote server?**

```
├── API token valid?
│   ├── No → Generate new token in DataRobot UI
│   └── Yes → Check token format
├── Correct Bearer format?
│   ├── Should be: `Authorization: Bearer YOUR_API_TOKEN`
│   └── No spaces or extra characters
├── Token expired?
│   ├── Yes → Generate new token
│   └── No → Check permissions
└── Have deployment access?
    ├── Check DataRobot permissions
    └── Verify deployment ID is correct
```

### Claude Desktop specific issues

**Claude Desktop: Command Not Found?**

```
├── Node.js installed?
│   ├── No → Install: `brew install node` (macOS) or download from nodejs.org
│   └── Yes → Check version: `node --version`
├── npm global binaries in PATH?
│   ├── No → Add to PATH or use full path to npx
│   └── Yes → Test: `npx mcp-remote@latest --version`
└── mcp-remote package available?
    ├── Test: `npx mcp-remote@latest --version`
    └── Should return version information
```

### Quick diagnostic commands

> **Note**: For server verification commands, see the [Server verification](#server-verification) section above.

**Test API token:**

```bash
curl -H "Authorization: Bearer $DATAROBOT_API_TOKEN" $DATAROBOT_ENDPOINT/api/v2/projects/ | head -1
# Expected: {"count": ...} or similar JSON response
```

**Check port availability:**

```bash
lsof -i :8080
# Expected: Empty output or process you can kill
```

### Still having issues?

If the decision tree doesn't solve your problem:

1. **Check client logs** for specific error messages
2. **Check server logs** for startup or runtime errors  
3. **Verify all prerequisites** are met
4. **Test with a different client** (e.g., try Cursor if VSCode fails)
5. **Check the [Additional Resources](#additional-resources)** section for more help

## Advanced features (optional)

> **When to use:** Only enable these features if you need specific functionality like dynamic tool registration, memory management, or OpenTelemetry tracing. Most users can skip this section.

### Dynamic tool registration

**Use case:** When you have multiple DataRobot deployments that should be auto-discovered as tools.

Dynamic tool registration allows the MCP server to automatically discover and register external tools deployed as DataRobot custom models. This enables a modular architecture where tools can be developed, deployed, and managed independently from the main MCP server.

#### Enable auto-registration

Set the environment variable:

```bash
MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP=true
```

#### Tool requirements

For a deployment to be auto-registered as a tool:

1. **Tagged**: Deployment must have a tag with name=`tool` and value=`tool`
2. **Active**: Deployment must be active and accessible
3. **Metadata Endpoint**: Must expose `/info/` route returning tool metadata

For complete documentation, see the [Dynamic Tool Registration Guide](./dynamic_tool_registration.md).

### Dynamic prompt registration

**Use case:** When you have multiple DataRobot prompts that should be auto-discovered as prompts.

Dynamic prompt registration allows the MCP server to automatically discover and register DataRobot prompts.

#### Enable auto-registration

Set the environment variable:

```bash
MCP_SERVER_REGISTER_DYNAMIC_PROMPTS_ON_STARTUP=true
```

### OpenTelemetry tracing

**Use case:** When you need distributed tracing for debugging and monitoring.

The server automatically instruments:

- **HTTP Requests**: When HTTP instrumentors are enabled
- **Tool Executions**: Traces tool calls with parameters and results
- **Error Tracking**: Captures exceptions and errors
- **Custom Spans**: Add your own tracing spans

Configure tracing via environment variables:

```bash
OTEL_ENABLED=true
OTEL_COLLECTOR_BASE_URL=https://your-otel-endpoint
OTEL_ENTITY_ID=your-entity-id
```

View traces in your configured OTEL collector or DataRobot's built-in tracing interface.

### Feature flag validation

**Use case:** When deploying to DataRobot instances with specific feature requirements.

Ensure required DataRobot features are enabled before deployment by adding YAML files to `infra/feature_flags/`:

```yaml
# infra/feature_flags/mcp_features.yaml
---
ENABLE_MLOPS: true
ENABLE_PUBLIC_NETWORK_ACCESS_FOR_ALL_CUSTOM_MODELS: true
```

The deployment will fail early if required features are not enabled on your DataRobot instance.

---

## Additional resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Cursor MCP Documentation](https://docs.cursor.com/)
- [Claude Desktop Documentation](https://www.anthropic.com/claude/desktop)