# Hello Ticket Orchestrator

Minimal two-agent orchestrator that exercises the Linear and Smartsheet MCP servers with a
simple planning-and-delivery scenario.

## Architecture

The orchestrator uses a **modular prompt architecture**:

- **Agent Personas** (Aanya the Planner, Arjun the Engineer) - Define *who* the agents are
- **World/Scenario Prompts** - Define *what* they're trying to accomplish
- **Composed at Runtime** - Personas + Scenario = Complete system prompt

This separation allows you to reuse the same agents across different scenarios (bug triage, sprint planning, feature specs, etc.) without rewriting agent identities.

See [SCENARIOS.md](./SCENARIOS.md) for detailed documentation and examples.

## Default Scenario: "Hello Ticket"

- Planner agent creates or updates a Smartsheet row with three to four acceptance criteria.
- Engineer agent discovers an appropriate Linear team/project, creates one issue, links it to the
  Smartsheet row, progresses status to `Done`, and leaves a progress comment.
- Both agents can read/write both systems, but the planner defaults to Smartsheet writes and the
  engineer to Linear writes. Cross-writes require an explicit acknowledgement turn.

## Prerequisites

1. Python 3.11+
2. `uv` package manager installed.
3. Smartsheet FastAPI server running locally at `http://127.0.0.1:8000`:
   ```bash
   cd /Users/apple/Github/mcp-ai-lab/smartsheet
   uv sync
   uv run alembic upgrade head  # once
   uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

## Setup

```bash
cd /Users/apple/Github/research/orchestrator
uv sync
cp .env.example .env
```

Edit `.env` and set:

```env
# Required
OPENAI_API_KEY=sk-...

# OpenAI Configuration (optional overrides)
OPENAI_MODEL=gpt-4o-mini      # default: gpt-4o-mini
OPENAI_TEMPERATURE=0.3        # default: 0.3
OPENAI_SEED=42                # optional for reproducibility

# Run Configuration (optional overrides)
MAX_TURNS=20                  # default: 20 - maximum conversation turns
STALE_TURN_LIMIT=4            # default: 4 - turns without activity before stopping
REFLECTION_INTERVAL=6         # default: 6 - turns between reflection prompts
LOG_DIR=runs                  # default: runs - directory for log files

# MCP Server Commands (optional overrides)
SMARTSHEET_MCP_CMD=python /Users/apple/Github/mcp-ai-lab/smartsheet/main_mcp.py
LINEAR_MCP_CMD=uv --directory /Users/apple/Github/mimicry-club run python -m apps.linear.mcp
```

## Run

### Default Scenario (Hello Ticket)

```bash
uv run python main.py
```

### Run with Different Scenarios

```bash
# Run bug triage workflow
python examples.py bug_triage

# Run sprint planning workflow
python examples.py sprint_planning

# Run documentation sync workflow
python examples.py documentation_sync
```

### Run with Custom Configuration

You can override run parameters via environment variables:

```bash
# Run with more turns and different stale limit
MAX_TURNS=30 STALE_TURN_LIMIT=6 uv run python main.py

# Run sprint planning with custom parameters
MAX_TURNS=25 REFLECTION_INTERVAL=10 python examples.py sprint_planning

# Use a different log directory
LOG_DIR=my_logs python examples.py bug_triage
```

The orchestrator will:

1. Launch Smartsheet and Linear MCP servers via stdio.
2. Perform health probes:
   - `smartsheet.health_check`
   - `linear.list_teams(limit=1)`
3. Alternate turns between Planner and Engineer until success or stop condition.
4. Log every turn to `runs/<scenario_name>_<timestamp>.jsonl` (messages, tool calls, results, tokens).
   - Default scenario: `runs/hello_ticket_<timestamp>.jsonl`
   - Bug triage: `runs/bug_triage_and_investigation_<timestamp>.jsonl`
   - Sprint planning: `runs/sprint_planning_<timestamp>.jsonl`
   - Documentation sync: `runs/documentation_sync_<timestamp>.jsonl`

See [SCENARIOS.md](./SCENARIOS.md) for creating custom scenarios.

## Next Steps

- Add stricter success assertions (automatic verification of cross-links and status transitions).
- Support WebSocket transports to enable a docker-compose deployment.
- Expand scenarios (labels, cycles, docs-guided fixes) once the core loop is stable.
