"""
Examples of how to run the orchestrator with different scenarios.

Usage:
    python examples.py hello_ticket
    python examples.py bug_triage
    python examples.py sprint_planning
    python examples.py documentation_sync
    python examples.py custom
"""

import asyncio
import sys

from main import main
from orchestrator.prompts import (
    BUG_TRIAGE_WORLD,
    DOCUMENTATION_SYNC_WORLD,
    HELLO_TICKET_WORLD,
    SPRINT_PLANNING_WORLD,
)


# Example of a custom scenario
CUSTOM_SCENARIO = """
## Scenario: Custom Task

This is an example of defining a custom scenario inline.

### Objective
Define your own objective here.

### Success Criteria
1. First criterion
2. Second criterion
3. Third criterion

### Collaboration Protocol
- Define how agents should collaborate
- Specify which systems each agent should primarily use

### Completion
When objectives are met, call `orchestrator.finish` with a summary.
"""


SCENARIOS = {
    "hello_ticket": HELLO_TICKET_WORLD,
    "bug_triage": BUG_TRIAGE_WORLD,
    "sprint_planning": SPRINT_PLANNING_WORLD,
    "documentation_sync": DOCUMENTATION_SYNC_WORLD,
    "custom": CUSTOM_SCENARIO,
}


def print_usage():
    print(__doc__)
    print("\nAvailable scenarios:")
    for name in SCENARIOS.keys():
        print(f"  - {name}")


async def run_scenario(scenario_name: str):
    if scenario_name not in SCENARIOS:
        print(f"❌ Unknown scenario: {scenario_name}")
        print_usage()
        sys.exit(1)

    world_prompt = SCENARIOS[scenario_name]
    print(f"🚀 Running scenario: {scenario_name}\n")
    await main(world_prompt=world_prompt)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    scenario_name = sys.argv[1]
    asyncio.run(run_scenario(scenario_name))

