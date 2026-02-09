# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
- Fix empty last name validation issue in user create for fastapi_server backend
- Fix for Taskfile removed in derived repositories
- Fix missing trailing slash for URL service links in terminal print for task dev
- Fix broken link for prompt management in README
- Removed shortcuts for frontend dev server
- Fix task agent:dev-stop
- UI: Added confirmation dialog when removing chat
- Removed Chainlit ui
- Switch root `task dev` to use shared `drdev` from `datarobot`
- Added MCP configuration options to select specific tools
- Make agent package flat
- Configuration of the local development port of the agent is done via the AGENT_PORT instead of the AGENT_ENDPOINT environment variable
- Add `agent/AGENTS.md` documentation describing how to customize and extend the default LangGraph agent
- Introduce Pulumi LLM infrastructure options for both LLM Gateway–backed models and existing registered LLM deployments
- Open source MCP server AF component
- Move the Gdrive tools to the DR GEN AI library.
- Upgrade drmcp dependency to include integration tools: Gdrive, Microsoft SharePoint, Jira and Confluence
- Add Microsoft OAuth support
- Updated `agent/AGENTS.md` and added root level `AGENTS.md` file with the instructions on how to implement/deploy agents using supported AI frameworks

## 11.4.6
- Fix for task dev in codespaces
- Fix for dr start procedure
- UI: Fix active send button when user input is empty

## 11.4.5
- Add release pipeline overrides
- MCP Server migrate to use GenAI Agents image by default
- `task dev` tracks start of all processes, and only shows status after all processes actually started
- `task dev` shows only URL of a frontend service
- Several README improvements
  - Install prerequisite tools: add version check note and link to new "Detailed installation commands" section.
  - New "Detailed installation commands": copy‑paste commands for macOS (Homebrew) and Linux (apt/curl) for dr-cli, git, uv, Pulumi, Taskfile, and node.
  - Setup guidance: note for DataRobot codespaces to expose ports; expanded wizard walkthrough (Use Case ID instructions; Pulumi stack name constraint); bolded Chainlit playground section title.
  - Troubleshooting: add "DataRobot codespace port configuration" subsection with explanation and image; clarify fixed vs configurable ports.
  - Minor copy/clarity edits and reorganization of tips/notes.

## 11.4.4
- Fix not publishing fastapi_server/static directory

## 11.4.3
- Fix devcontainers configuration

## 11.4.2
- Rename custom_model to agentic_workflow
- Rename web to fastapi_server
- Fix tracing when using threading
- Display tool invocations and results on the UI
- Implement background chats
- Fix mapping for chat history endpoint

## 11.4.0
- Reduce agents to just planner and writer
- Fix the default model used everywhere to be a non-deprecated model
- Fix issues related to docker_context usage in infra and move logic to fixed pulumi for version pinning
- Fix NAT streaming
- Event streaming for langgraph
- Add parameter DATABASE_URI to setup wizard
- Fix devcontainer configuration
- Fix execution environment pinning in edge case with blank version id
- Fix CVEs
- Remove temperature from NAT workflow.yaml

## 11.3.4
- Add versions file

## 11.3.3
- Fix the root Taskfile

## 11.3.2
- Improvements to dev containers and start experience

## 11.3.1
- Fix error handling in UI
- Remove mastra dependencies
- Full dr start experience
- Fix autoscroll behavior
- OAuth fixes

## 11.3.0
- Fix devcontainer not compiling Dockerfile
- Restore missing chainlit lit.py
- Pin pulumi version so that it doesn't encounter github rate limiting
- Show an error message in case agent response is empty
- Fix migrations in task start

## 0.0.6

## 0.0.5

## 0.0.4

## 0.0.3

## 0.0.2

## 0.0.1
- Auto-select (and create) pulumi stack if env variable is present
- Upgrade datarobot in pyproject.toml
- Append pulumi stack name from environment if present to all pulumi commands
- Simplify all pulumi local and remote naming
- Initial implementation
