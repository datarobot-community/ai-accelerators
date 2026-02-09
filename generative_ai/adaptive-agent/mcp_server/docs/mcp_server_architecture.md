# Architecture

## Project structure

```
├── mcp_server/        # Main application code
│   ├── app/
│   │   ├── core/              # Core server logic, config, telemetry
│   │   │   ├── server_lifecycle.py
│   │   │   ├── user_config.py
│   │   │   └── user_credentials.py
│   │   ├── tools/             # DataRobot tools and custom tools
│   │   │   ├── user_tools.py
│   │   ├── prompts/           # Prompt templates
│   │   ├── resources/         # Resources
│   │   └── main.py            # Application entry point
│   ├── static/                # Static assets
│   │   └── assets/img/        # Images and icons
│   ├── pyproject.toml         # Python dependencies
│   ├── Taskfile.yaml          # Development tasks
│   ├── metadata.yaml          # Application metadata
│   ├── user-metadata.yaml     # User-specific metadata
│   ├── uv.lock                # UV lock file
├── docs/                      # Documentation
│   ├── custom_tools.md
│   ├── deployment_info_tools.md
│   ├── dynamic_tool_registration.md
│   ├── mcp_client_setup.md
│   └── mcp_server_architecture.md
├── img/                       # Documentation images
├── infra/                     # Infrastructure as Code (Pulumi)
│   ├── docker/                # Docker build configuration
│   ├── infra/                 # Pulumi infrastructure definitions
│   ├── feature_flags/         # DataRobot feature flag validation
│   ├── __main__.py            # Pulumi entry point
│   ├── pyproject.toml         # Infrastructure dependencies
│   ├── Taskfile.yaml          # Infrastructure tasks
│   └── uv.lock                # UV lock file
├── AUTHORS                    # Project authors
├── CHANGELOG.md               # Change log
├── CODE_OF_CONDUCT.md         # Code of conduct
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # License file
├── LICENSE.txt                # License text
├── README.md                  # Main README
├── RELEASE.yaml               # Release configuration
├── Taskfile.yaml              # Top-level task orchestration
└── trivy-ignore.rego          # Security scan ignore rules
```

## Application structure

The template provides a streamlined structure for building MCP servers:

- **Core** (`app/core/`): Core server logic, configuration, and lifecycle management
- **Tools** (`app/tools/`): DataRobot tools and custom tool implementations
- **Resources** (`app/resources/`): Static resources and assets
- **Prompts** (`app/prompts/`): Prompt templates for AI interactions

This structure allows you to:

- Organize code by functionality rather than abstraction layers
- Easily add custom tools and configurations
- Keep resources and prompts organized and accessible

## Configuration

### Environment variables

| Variable              | Description            | Default                     |
|-----------------------|------------------------|-----------------------------|
| `DATAROBOT_API_TOKEN` | DataRobot API token    | -                           |
| `DATAROBOT_ENDPOINT`  | DataRobot instance URL | `https://app.datarobot.com` |

### MCP server configuration

| Variable               | Description           | Default                |
|------------------------|-----------------------|------------------------|
| `MCP_SERVER_NAME`      | Server display name   | `datarobot-mcp-server` |
| `MCP_SERVER_PORT`      | Server port           | `8080`                 |
| `MCP_SERVER_HOST`      | Server host address   | `0.0.0.0`              |
| `MCP_SERVER_LOG_LEVEL` | MCP server log level  | `WARNING`              |
| `APP_LOG_LEVEL`        | Application log level | `INFO`                 |

### Advanced configuration

<details>
<summary>Dynamic Tool Registration</summary>

| Variable                                          | Description                    | Default |
|---------------------------------------------------|--------------------------------|---------|
| `MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP`    | Auto-register tools on startup | `false` |
| `MCP_SERVER_TOOL_REGISTRATION_DUPLICATE_BEHAVIOR` | How to handle duplicate tools  | `warn`  |

</details>


<details>
<summary>Dynamic Prompt Registration</summary>

| Variable                                            | Description                      | Default |
|-----------------------------------------------------|----------------------------------|---------|
| `MCP_SERVER_REGISTER_DYNAMIC_PROMPTS_ON_STARTUP`    | Auto-register prompts on startup | `false` |
| `MCP_SERVER_PROMPT_REGISTRATION_DUPLICATE_BEHAVIOR` | How to handle duplicate prompts  | `warn`  |

</details>

<details>
<summary>OpenTelemetry configuration</summary>

| Variable                          | Description                   | Default                 |
|-----------------------------------|-------------------------------|-------------------------|
| `OTEL_ENABLED`                    | Enable OpenTelemetry tracing  | `true`                  |
| `OTEL_COLLECTOR_BASE_URL`         | OTEL collector endpoint       | Uses DataRobot endpoint |
| `OTEL_ENTITY_ID`                  | Entity ID for traces          | -                       |
| `OTEL_ENABLED_HTTP_INSTRUMENTORS` | Enable HTTP instrumentation   | `false`                 |
| `OTEL_ATTRIBUTES`                 | Custom OTEL attributes (JSON) | `{}`                    |

</details>

<details>
<summary>AWS configuration</summary>

| Variable                    | Description               | Default |
|-----------------------------|---------------------------|---------|
| `AWS_ACCESS_KEY_ID`         | AWS access key            | -       |
| `AWS_SECRET_ACCESS_KEY`     | AWS secret key            | -       |
| `AWS_SESSION_TOKEN`         | AWS session token         | -       |
| `AWS_PREDICTIONS_S3_BUCKET` | S3 bucket for predictions | -       |
| `AWS_PREDICTIONS_S3_PREFIX` | S3 prefix for predictions | -       |

</details>

## Custom configuration

Add custom configuration in `mcp_server/app/core/user_config.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class CustomAppConfig(BaseSettings):
    app_name: str = Field(
        default="my-custom-mcp-server",
        description="Name of your MCP server"
    )
    
    # Add your custom configuration fields here
    custom_api_endpoint: str = Field(
        default="https://api.example.com",
        description="Your custom API endpoint"
    )
```

Configuration values are automatically loaded from environment variables or the `.env` file.