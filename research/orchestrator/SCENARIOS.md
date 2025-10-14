# Orchestrator Scenarios Guide

## Architecture Overview

The orchestrator now separates **agent personas** from **world/scenario prompts**:

```
┌─────────────────────────────────────────┐
│         World/Scenario Prompt           │
│  (What are we trying to accomplish?)    │
│  - Objective                            │
│  - Success criteria                     │
│  - Collaboration protocol               │
│  - Completion conditions                │
└─────────────────────────────────────────┘
                    +
┌─────────────────────────────────────────┐
│          Agent Persona Prompt           │
│     (Who am I and how do I work?)       │
│  - Core identity                        │
│  - Collaboration style                  │
│  - Operational guidelines               │
│  - Communication tone                   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Composed System Prompt          │
│   (Sent to LLM at runtime)              │
└─────────────────────────────────────────┘
```

This design allows you to:
- ✅ Reuse the same agents (Aanya & Arjun) across different scenarios
- ✅ Create new scenarios without modifying agent personas
- ✅ Mix and match different persona types with different scenarios
- ✅ Maintain clear separation of concerns

## Agent Personas

### Planner (Aanya)
- **Role**: Warm, incisive planner
- **Strengths**: Clarifying requirements, breaking down features, maintaining traceability
- **Primary Tools**: Smartsheet (planning/spec tools)
- **Tone**: Confident, collaborative, slightly playful

### Engineer (Arjun)
- **Role**: Thoughtful, pragmatic engineer
- **Strengths**: Creating actionable work items, tracking progress, technical execution
- **Primary Tools**: Linear (engineering tools)
- **Tone**: Grounded, candid, collaborative

## Available Scenarios

### 1. Hello Ticket (Default)
**Purpose**: Simple feature spec-to-delivery workflow

**Flow**:
1. Planner creates Smartsheet row with 3-4 acceptance criteria
2. Engineer creates corresponding Linear issue
3. Both systems get cross-linked
4. Issue progresses: Open → In Progress → Done

**Best for**: Basic feature development, onboarding, testing the system

---

### 2. Bug Triage
**Purpose**: Investigate and route bugs efficiently

**Flow**:
1. Planner documents bug investigation in Smartsheet (reproduction, impact)
2. Engineer creates prioritized Linear issue with technical routing
3. Issue assigned to appropriate team
4. Both systems cross-linked

**Best for**: Bug tracking, incident management, QA workflows

---

### 3. Sprint Planning
**Purpose**: Plan and commit work for an upcoming sprint

**Flow**:
1. Planner manages capacity planning in Smartsheet
2. Engineer updates Linear issues with estimates and assignments
3. Issues moved to current cycle/sprint
4. Sprint goals documented in both systems

**Best for**: Agile planning, resource allocation, iteration planning

---

### 4. Documentation Sync
**Purpose**: Keep documentation consistent across systems

**Flow**:
1. Both agents review documentation in their respective systems
2. Identify and resolve discrepancies
3. Update cross-references
4. Document changes with comments

**Best for**: Maintaining stakeholder visibility, ensuring consistency

## Creating a Custom Scenario

### Step 1: Define the World Prompt

Create a new world prompt in `orchestrator/prompts.py`:

```python
MY_CUSTOM_WORLD = """
## Scenario: [Your Scenario Name]

[Brief description of the workflow]

### Objective
[What are we trying to accomplish?]

### Success Criteria
1. First measurable outcome
2. Second measurable outcome
3. Third measurable outcome

### Collaboration Protocol
- [How should Planner (Aanya) contribute?]
- [How should Engineer (Arjun) contribute?]
- [Any cross-system coordination rules?]

### Completion
When objectives are met, call `orchestrator.finish` with [what summary info?].
"""
```

### Step 2: Use It in Code

```python
from orchestrator.prompts import MY_CUSTOM_WORLD
from main import main

# Run with your custom scenario
await main(world_prompt=MY_CUSTOM_WORLD)
```

Or add it to `examples.py`:

```python
from orchestrator.prompts import MY_CUSTOM_WORLD

SCENARIOS = {
    # ... existing scenarios ...
    "my_custom": MY_CUSTOM_WORLD,
}
```

Then run:
```bash
python examples.py my_custom
```

## World Prompt Template

Use this template when creating new scenarios:

```markdown
## Scenario: [Name]

[One paragraph description of the workflow and context]

### Objective
[Clear, concise statement of what needs to be accomplished]

### Success Criteria
1. [Specific, measurable outcome]
2. [Specific, measurable outcome]
3. [Specific, measurable outcome]
4. [Optional: More criteria]

### Collaboration Protocol
- Planner (Aanya) [primary responsibilities and preferred tools]
- Engineer (Arjun) [primary responsibilities and preferred tools]
- [Any coordination rules, handoff points, or approval gates]

### Completion
When [condition], call `orchestrator.finish` with [expected summary content].
```

## Best Practices

### Do's ✅
- **Be specific about success criteria** - Agents need clear goals
- **Define collaboration boundaries** - Specify who owns what
- **Include completion triggers** - Tell agents when to call `orchestrator.finish`
- **Reference actual tool capabilities** - Match scenario to available MCP tools
- **Keep it focused** - One clear objective per scenario

### Don'ts ❌
- **Don't mix persona traits into scenarios** - Keep identity separate from task
- **Don't specify low-level implementation** - Let agents figure out the "how"
- **Don't create circular dependencies** - Avoid ambiguous handoffs
- **Don't forget the finish condition** - Agents need exit criteria
- **Don't overload with too many goals** - Keep scenarios bounded

## Advanced: Multi-Tool Scenarios

You can create scenarios that leverage multiple MCP servers:

```python
ADVANCED_WORKFLOW = """
## Scenario: Advanced Multi-System Workflow

### Objective
Coordinate work across Linear (issues), Smartsheet (specs), 
and [hypothetical third system] (deployments).

### Success Criteria
1. Issue created in Linear with links to spec
2. Spec documented in Smartsheet with deployment checklist
3. Deployment tracked in [third system] with issue reference
4. All three systems cross-linked

### Collaboration Protocol
- Planner manages specs and checklists
- Engineer manages issues and deployment coordination
- Both validate cross-references

### Completion
When all systems are linked and deployment is scheduled, 
call `orchestrator.finish` with all artifact URLs.
"""
```

## Logging and Observability

The run signature now logs:
- `world_prompt` - The scenario being executed
- `agent_personas` - The raw persona prompts
- `composed_prompts` - The final prompts sent to the LLM

Check `runs/hello_ticket_<timestamp>.jsonl` to see how prompts were composed.

## Example: Switching Scenarios

```python
# In your code
from orchestrator.prompts import (
    HELLO_TICKET_WORLD,
    BUG_TRIAGE_WORLD,
    SPRINT_PLANNING_WORLD,
)

# Run different scenarios
await main(world_prompt=HELLO_TICKET_WORLD)    # Default feature workflow
await main(world_prompt=BUG_TRIAGE_WORLD)      # Bug investigation
await main(world_prompt=SPRINT_PLANNING_WORLD) # Sprint planning
```

Or via command line:
```bash
python examples.py hello_ticket
python examples.py bug_triage
python examples.py sprint_planning
```

## Configuration Options

You can customize the orchestrator's behavior via environment variables:

### Run Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TURNS` | `20` | Maximum conversation turns before stopping |
| `STALE_TURN_LIMIT` | `4` | Turns without activity before stopping |
| `REFLECTION_INTERVAL` | `6` | Turns between reflection prompts |
| `LOG_DIR` | `runs` | Directory for log files |

### Example Usage

```bash
# Longer conversation for complex scenarios
MAX_TURNS=30 python examples.py sprint_planning

# More patience for slower scenarios
STALE_TURN_LIMIT=8 python examples.py bug_triage

# Custom log directory
LOG_DIR=sprint_logs python examples.py sprint_planning

# Combine multiple overrides
MAX_TURNS=25 STALE_TURN_LIMIT=6 REFLECTION_INTERVAL=10 python examples.py hello_ticket
```

## Next Steps

1. **Try the examples** - Run `python examples.py hello_ticket`
2. **Create your own scenario** - Use the template above
3. **Extend agent personas** - Add new agent types if needed
4. **Share scenarios** - Document effective scenarios for reuse
5. **Tune parameters** - Adjust `MAX_TURNS`, `STALE_TURN_LIMIT`, etc. for your needs

