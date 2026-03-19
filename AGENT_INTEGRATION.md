# Agent Integration Guide

## Overview

The `test_agents.py` file is now integrated with the Mars simulation to autonomously manage astronaut survival using AI agents.

## Installation

First, install the required dependencies:

```bash
cd hackathon
pip install -r requirements-agents.txt
```

Or install individually:
```bash
pip install strands-agents mcp boto3
```

## How It Works

The integration provides three key capabilities:

1. **State Monitoring**: Reads simulation state (astronaut health, plant status, food inventory, resources)
2. **Issue Detection**: Automatically identifies critical issues requiring intervention
3. **Autonomous Actions**: Agents analyze the situation and execute actions (watering, harvesting)

## Usage

### Run Autonomous Survival Management

Start the simulation in one terminal:
```bash
cd hackathon/simulation
python sim.py
```

In another terminal, start the autonomous agent system:
```bash
cd hackathon
python test_agents.py autonomous
```

The agents will:
- Monitor simulation state every day
- Detect critical issues (low hydration, food shortages, harvestable crops)
- Consult the AI swarm (environment + nutrition agents)
- Execute recommended actions automatically

### Run Original Tests

To run the original agent tests without autonomous mode:
```bash
cd hackathon
python test_agents.py
```

## Key Functions

### `get_simulation_state()`
Returns current simulation state as a dictionary for agent analysis.

### `analyze_critical_issues()`
Scans simulation and returns list of issues:
- Astronaut health warnings (hydration, cognitive, nutrition)
- Plant health alerts (wilting, low hydration)
- Harvest opportunities
- Food/water supply warnings

### `execute_action(action, target)`
Executes actions on the simulation:
- `harvest` - Harvest a specific plant
- `water` - Water a specific plant
- `water_all` - Water all plants

### `run_autonomous_survival_management()`
Main loop that:
1. Checks simulation state periodically
2. Identifies issues
3. Consults AI agents
4. Executes recommended actions

## Agent Architecture

The system uses a **Swarm multi-agent pattern**:

- **Environment Agent**: Manages greenhouse conditions, plant health, water resources
- **Nutrition Agent**: Monitors crew health, food inventory, nutritional balance

Agents collaborate through handoffs to make holistic decisions about crew survival.

## Example Output

```
--- Day 15 Check ---
Found 3 issue(s):
  • WARNING: Lettuce low hydration (35%)
  • ACTION: Radish ready for harvest (2.1 kg)
  • WARNING: 12.3 days of food remaining

Consulting agents...

Agent Response (success):
Based on the current state, I recommend:
1. Harvest the Radish immediately to boost food supply
2. Water the Lettuce to prevent wilting
3. Monitor Potato growth for next harvest cycle

✓ Harvested 2.10 kg of Radish
✓ Watered Lettuce
```

## Configuration

Edit these variables in `test_agents.py`:
- `check_interval_days`: How often to check simulation (default: 1 day)
- `max_days`: When to stop monitoring (default: 450 days)
- `MCP_URL`: Knowledge base endpoint
- `MODEL`: AI model to use
