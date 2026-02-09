# MCP server

An MCP server is a utility that allows the agent to access tools.
The template is configured to automatically connect the agent with an MCP server both locally and in a deployed setting.

## Testing against remote servers

When testing locally, the MCP server connects to a local instance running at `http://localhost:9000` by default (see [Ports reference](../README.md#ports-reference) for all port information).
To modify the port, set the `MCP_SERVER_PORT` environment variable in your `.env` file.

To test against remote MCP Servers:

1. Set the `MCP_DEPLOYMENT_ID` environment variable to test against a deployed MCP server in DataRobot.
2. Set the `EXTERNAL_MCP_URL` environment variable to connect to an external MCP server endpoint (for example: `https://example.com/mcp`).
  
  > [!NOTE]
  > DataRobot bearer tokens and OAuth context are not forwarded to external MCP servers.
  > To send custom headers, set the `EXTERNAL_MCP_HEADERS` environment variable to a JSON string (e.g., `'{"Authorization":"Bearer token123","X-Custom-Header":"value"}'`); it will be parsed using `json.loads()`.
  > To change the transport for MCP server, set the `EXTERNAL_MCP_TRANSPORT` environment variable to `sse` or `streamable-http` (default).

3. When running `dr task run deploy`, the project automatically deploys the MCP server from your project, which takes precedence over any MCP Servers configured via environment variables for testing purposes.
