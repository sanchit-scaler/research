# Tool Integration Scenario

## Overview

The **Tool Integration** scenario features a 4-agent team tasked with figuring out how to effectively use a newly adopted Smartsheet system alongside their existing Linear installation.

### The Setup

- **Linear**: Contains years of operational history (5500 users, 5 teams, 5 projects, 30,000+ issues)
- **Smartsheet**: Brand new, completely empty, expensive investment that needs justification
- **The Challenge**: Make Smartsheet valuable without disrupting existing Linear workflows

## The 4-Agent Team

### 1. Alex Chen - Director of Operations (Strategic)
**Role**: Championed the Smartsheet purchase, now accountable for ROI

**Characteristics**:
- Strategic thinker who needs to justify the investment
- Understands change management - won't force tools on people
- Balances innovation with respect for existing workflows
- Makes final decisions when team is stuck

**Tool Behavior**:
- Explores Linear to understand current state
- Creates strategic frameworks and documentation in Smartsheet
- Links systems to maintain traceability

### 2. Sam Rivera - Engineering Manager (Skeptical)
**Role**: Long-time Linear power user, protective of engineering workflows

**Characteristics**:
- Been using Linear for 3+ years - knows it intimately
- Naturally skeptical - has seen too many "solutions" create problems
- Fair-minded - will support Smartsheet if shown clear value
- Direct, pragmatic, evidence-based

**Tool Behavior**:
- References existing Linear data frequently
- Points out what Linear already does well
- Cautiously experiments with Smartsheet
- Creates clear boundaries about tool usage

### 3. Jordan Park - Product Operations Lead (Enthusiastic)
**Role**: Works across functions, frustrated by Linear's engineering-centric design

**Characteristics**:
- Needs visibility for non-technical stakeholders
- Excited about Smartsheet's potential
- Eager to experiment and demonstrate value
- Solutions-oriented and creative

**Tool Behavior**:
- Extracts insights from Linear data
- Builds Smartsheet dashboards and reports
- Creates cross-functional artifacts
- Demonstrates quick wins

### 4. Taylor Kim - Business Analyst (Analytical)
**Role**: Responsible for organizational insights, sees Smartsheet as analytics layer

**Characteristics**:
- Has questions Linear's reporting can't answer
- Data-driven decision maker
- Identifies patterns and trends
- Makes data accessible and actionable

**Tool Behavior**:
- Deep Linear exploration and analysis
- Transforms Linear data into Smartsheet insights
- Creates metrics dashboards and reports
- Surfaces insights that drive decisions

## The Scenario Prompt

```markdown
## Scenario: New Tool Adoption

Leadership recently purchased Smartsheet licenses for the organization. The tool is 
currently empty and unused. Meanwhile, Linear has been the team's primary system 
for years.

### Your Situation
You are a cross-functional working group tasked with making Smartsheet valuable to 
the organization.

### What You Know
- Smartsheet is new, empty, and expensive
- Linear contains the organization's operational history
- Leadership expects ROI on the Smartsheet investment
- The team needs to figure out how these tools should work together

### What Success Looks Like
The team decides for themselves, but successful adoption might include:
- Smartsheet contains valuable content that serves a clear purpose
- The organization understands when to use which tool
- Both tools are actively used without creating confusion
- The investment is justified

### Constraints
- Don't disrupt existing workflows unnecessarily
- Don't duplicate effort across systems
- Make data-driven decisions
- Build consensus across different perspectives

The team has autonomy to discover the right approach.
```

## Expected Behavior Patterns

### Early Turns - Discovery
1. **Alex** explores Linear to understand scale and current usage
2. **Sam** defends Linear's strengths, questions need for Smartsheet
3. **Jordan** identifies gaps where Linear falls short
4. **Taylor** analyzes Linear data to surface insights

### Middle Turns - Experimentation
- Jordan builds portfolio views and dashboards in Smartsheet
- Taylor creates analytics that Linear can't provide
- Sam identifies specific use cases where Smartsheet adds value
- Alex synthesizes findings into coherent integration model

### Later Turns - Standardization
- Team establishes clear "use Linear for X, Smartsheet for Y" guidelines
- Cross-references between systems are documented
- Templates and best practices emerge
- ROI is demonstrated through actual artifacts

## Why This Scenario Works

### 1. No Execution Gap
Every action is a real tool operation:
- ✅ "I'll create a Smartsheet dashboard" → Actually creates it
- ✅ "I'll analyze Linear data" → Actually searches and analyzes
- ✅ "I'll document the strategy" → Creates Smartsheet doc
- ❌ "I'll implement the feature" → Would be a hallucination

### 2. Realistic Organizational Dynamics
- Tool skepticism (Sam)
- Cross-functional needs (Jordan)
- Data-driven decisions (Taylor)
- Strategic oversight (Alex)

### 3. Emergent Patterns
The team discovers:
- What belongs in each system
- How to link systems effectively
- When to use which tool
- Best practices through experimentation

### 4. Rich Data Generation

**Linear** (existing → enhanced):
- New epic: "Smartsheet Integration Initiative"
- Integration-related issues
- Comments with Smartsheet URLs
- Labels tracking integration work

**Smartsheet** (empty → populated):
- Strategic documents (adoption strategy, usage guidelines)
- Portfolio views (all Linear projects summarized)
- Analytics dashboards (velocity, capacity, trends)
- Operational artifacts (templates, protocols)

## Running the Scenario

```bash
# Using examples.py
python examples.py tool_integration

# Or programmatically
python -c "import asyncio; from main import main; from orchestrator.prompts import TOOL_INTEGRATION_WORLD; asyncio.run(main(TOOL_INTEGRATION_WORLD))"
```

## Configuration

The tool integration scenario uses adjusted parameters for 4 agents:

```python
max_turns = 40              # More turns for 4 agents
stale_turn_limit = 6        # More tolerance
reflection_interval = 8     # Every 2 full rounds (2 × 4 agents)
max_tool_rounds = 8         # More exploration per turn
```

## Expected Artifacts

After a successful run, you should see:

### In Smartsheet:
1. **Strategic Layer**
   - Tool Adoption Strategy
   - Tool Usage Guidelines
   - Integration Protocols

2. **Portfolio Views**
   - All Projects Summary
   - Cross-Team Tracker
   - OKR Dashboard

3. **Analytics**
   - Velocity Dashboard
   - Team Capacity Analysis
   - Delivery Trends
   - Cycle Time Metrics

4. **Operational**
   - Process Templates
   - Data Sync Protocol
   - Cross-Reference Guide

### In Linear:
- Epic: "Smartsheet Integration Initiative"
- Issues tracking integration tasks
- Comments referencing Smartsheet docs
- Updated descriptions with Smartsheet links

## Key Differences from 2-Agent Scenarios

| Aspect | 2-Agent | 4-Agent Tool Integration |
|--------|---------|--------------------------|
| **Agents** | Planner, Engineer | Alex, Sam, Jordan, Taylor |
| **Dynamics** | Collaborative | Realistic org tensions |
| **Perspectives** | Aligned | Diverse (strategic, skeptical, enthusiastic, analytical) |
| **Communication** | Direct handoff | Broadcast to all teammates |
| **Decision Making** | Quick consensus | Requires building agreement |
| **Execution** | Abstract tasks | Real tool operations only |
| **Data Generation** | Linked artifacts | Comprehensive system integration |

## Success Metrics

You can evaluate success by:
1. **Smartsheet population**: How many meaningful artifacts created?
2. **Cross-references**: How well are systems linked?
3. **Tool boundaries**: Did clear usage patterns emerge?
4. **Consensus building**: Did skeptic (Sam) get convinced?
5. **Analytics value**: Do dashboards provide genuine insights?
6. **ROI justification**: Can Alex articulate the value?

## Future Enhancements

This scenario could be extended with:
- More agents (e.g., Executive Sponsor, End User)
- Event-based turn-taking instead of round-robin
- Memory/reflection mechanisms from research papers
- Automatic success metric calculation
- Multi-phase workflow (discovery → pilot → adoption)

