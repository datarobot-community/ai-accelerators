# Tensile – Enhancing agent reliability through automated test synthesis

This accelerator introduces [Tensile](https://github.com/datarobot-community/ai-accelerators/tree/main/tensile), DataRobot's test-driven development framework for improving the reliability, task performance, and policy adherence of AI agents.

## What's in this accelerator

The notebook walks through the **Enhanced Agent Improvement Cycle**:

1. **Instrument** an agent with `TrajectoryLogger` to record execution trajectories
2. **Analyze** trajectories to identify testable moments (successes and failures)
3. **Evaluate** and **replay** runs to quantify improvements and compare system prompt changes
4. **Configure** Tensile with the DataRobot LLM Gateway
5. Use **clustering** (Dash app and `ClusteringHintInjector`) to explore issues and inject contextual hints
6. Apply the **Trajectory Analyzer** workflow with `ProgrammaticHintInjector` for iterative improvement

## Prerequisites

- Tensile installed (see [tensile/README.md](https://github.com/datarobot-community/ai-accelerators/blob/main/tensile/README.md) for quickstart)
- `config.yaml` with LLM and trajectory settings
- For DataRobot: set `DATAROBOT_API_TOKEN` in `test.env` (or in your environment)

## Files

| File | Description |
|------|-------------|
| `tensile_agent_reliability.ipynb` | Step-by-step notebook for instrumenting, analyzing, and improving agents |
| `tensile_agent_reliability.config.yaml` | Accelerator metadata for the catalog |
| `test.env` | Template for API token and optional LLM Gateway URL |

For full framework details, CLI reference, and configuration options, see the main [tensile README](../../tensile/README.md).
