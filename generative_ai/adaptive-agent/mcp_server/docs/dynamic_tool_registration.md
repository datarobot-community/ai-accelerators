## Dynamic Tool Registration

Turn DataRobot deployments into LLM tools automatically. The MCP server proxies tool calls to your deployments.

### Quick Start

1. Deploy your model/service to DataRobot
2. Tag deployment with `tool` (both name and value)
3. **Done!** (DataRobot native models and DRUM work with zero config)

**Enable auto-discovery on startup (optional):**
```bash
MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP=true
```


---

## What Works Out of the Box

| Deployment Type                                                   | Configuration Needed                                                     |
|-------------------------------------------------------------------|--------------------------------------------------------------------------|
| **DataRobot native predictive models** (binary, regression, etc.) | ✅ None - just tag as `tool`                                              |
| **DRUM structured predictions**                                   | ✅ None (optional: add customized `inputSchema` in `model-metadata.yaml`) |
| **DRUM agentic workflows**                                        | ✅ None (optional: add customized `inputSchema` in `model-metadata.yaml`) |
| **DRUM unstructured**                                             | ⚠️ Must define `inputSchema` in `model-metadata.yaml`                    |
| **Custom servers** (FastAPI, etc.)                                | ⚠️ Must expose `/info/` endpoint with metadata                           |


**Note**: Registering other MCP Servers as tools, using dynamic tool registration, is not supported.

---

## Registration Requirements

**All deployments must:**
- Be tagged with `tool` (both name and value)
- Be active

**DataRobot native models:**
- No additional requirements

**DRUM deployments:**
- For unstructured: Define `inputSchema` in `model-metadata.yaml`
- For others: Optional, fallback schemas provided

**Custom servers:**
- Must expose `/info/` endpoint returning: `endpoint`, `method`, `input_schema`

--- 

### Runtime API
To manage tool registrations at runtime, use the following endpoints:

- `GET /registeredDeployments/` - List tools
- `PUT /registeredDeployments/{deployment_id}` - Register tool
- `DELETE /registeredDeployments/{deployment_id}` - Remove tool

---

## DRUM Deployments

[DataRobot DRUM](https://pypi.org/project/datarobot-drum/) deployments work with minimal configuration.

### Zero Configuration (Most Cases)

Deploy your model, tag as `tool`, and you're done:
- **Structured predictions** (binary, regression, multiclass, etc.): Auto-configured
- **Agentic workflows**: Auto-configured
- **DataRobot native models**: Auto-configured

### Unstructured Models (Configuration Required)

For `unstructured` target type, add `inputSchema` to `model-metadata.yaml`:

```yaml
name: "Fetch dataset"
description: "Fetches a dataset from DataRobot Data Registry"
type: inference
targetType: unstructured
inputSchema:
  type: object
  properties:
    json:
      type: object
      properties:
        dataset_id:
          type: string
          description: Dataset ID from Data Registry
        limit:
          type: integer
          default: 100
      required:
        - dataset_id
```

**Notes:** 
    - All parameters must be under `json` property for unstructured models (see Input Schema Reference below).
    - Exposing input schemas as metadata from `model-metadata.yaml` is supported in `datarobot-drum` version 1.17.2 and later.

### Custom Schema (Optional)

Override fallback schemas for better LLM guidance and more control over request structure:

```yaml
inputSchema:
  type: object
  properties:
    data:
      type: string
      description: "CSV with columns: transaction_amount, user_age, merchant_category"
  required:
    - data
```

---

## Custom Servers

For FastAPI, Flask, or other frameworks, expose an `/info/` endpoint with metadata.

### Required `/info/` Response

```json
{
  "endpoint": "/weather/{city}",
  "method": "GET",
  "input_schema": { /* JSON schema */ }
}
```

### FastAPI Example

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class WeatherRequest(BaseModel):
    class PathParams(BaseModel):
        city: str = Field(description="City name")
    
    class QueryParams(BaseModel):
        units: str = Field(default="metric", description="metric or imperial")
    
    path_params: PathParams
    query_params: QueryParams | None = None

@app.get("/info/")
async def metadata():
    return {
        #  Note: custom model deployments expose custom server endpoints behind 'directAccess/'
        "endpoint": "directAccess/weather/{city}",       
        "method": "GET",
        "input_schema": WeatherRequest.model_json_schema()
    }

@app.get("/weather/{city}")
async def get_weather(city: str, units: str = "metric"):
    return {"city": city, "temp": 22, "units": units}
```

### How the Weather Tool Works

**LLM calls the tool:**
```json
{
  "path_params": {"city": "paris"},
  "query_params": {"units": "imperial"}
}
```

**MCP server makes HTTP request:**
```
GET <base_url>/directAccess/weather/paris?units=imperial
```

Notes: 
 - **base_url**: Address will be determined automatically based on your DataRobot deployment (e.g. `https://app.datarobot.com/api/v2/deployments/<deployment-id>`)
 - **directAccess/**: When deployed in custom models, custom server endpoints are exposed under this path prefix.

---

## Input Schema Reference

### Parameter Groups

The weather example above demonstrates how parameters map to HTTP requests:

| Group | Purpose                     | Example from above |
|-------|-----------------------------|-------------------|
| `path_params` | URL path substitution       | `{city}` → `"paris"` |
| `query_params` | URL query string            | `?units=metric` |
| `data` | Raw request body (i.e. CSV) | Not used in weather example |
| `json` | JSON request body           | Not used in weather example |

### Rules

- `path_params` and `query_params` must be flat (no nested objects)
- `data` and `json` support nesting
- All `{param}` in endpoint must exist in `path_params`
- Empty schemas allowed with: `MCP_SERVER_TOOL_REGISTRATION_ALLOW_EMPTY_SCHEMA=true`

### Under the Hood

When an LLM calls the weather tool, the MCP server transforms it into an HTTP request:

```python
# What the MCP server does internally
async with session.request(
    method="GET",                                    # from /info/ metadata
    url="<base_url>/directAccess/weather/paris",    # base_url + endpoint with path_params
    params={"units": "imperial"}                    # query_params
) as response:
    return await response.json()
```

**General mapping for all parameter types:**
- `path_params` → substituted into URL path: `/weather/{city}` → `/weather/paris`
- `query_params` → appended as query string: `?units=imperial`
- `data` → sent as raw body (CSV, form data, etc.)
- `json` → sent as JSON body (mutually exclusive with `data`)

---

## Troubleshooting

### Tool Not Registering

```bash
# Check deployment is active and tagged
curl -H "Authorization: Bearer $DATAROBOT_API_TOKEN" \
  "$DATAROBOT_ENDPOINT/deployments/{deployment-id}/" | jq .

# Test /info/ endpoint (DRUM/Custom servers only)
curl -H "Authorization: Bearer $DATAROBOT_API_TOKEN" \
  "$DATAROBOT_ENDPOINT/deployments/{deployment-id}/directAccess/info/" | jq .

```

### Common Errors

| Error | Fix |
|-------|-----|
| Missing `input_schema` | Custom servers: add to `/info/` response<br>DRUM unstructured: add to `model-metadata.yaml` |
| Unsupported top-level property | Use only: `path_params`, `query_params`, `data`, `json` |
| Nested structure in path_params | Flatten it or move to `json` property |
| Missing path parameter | Define all `{variables}` in `path_params` |


