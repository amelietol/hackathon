# Agent Integration Guide

## Overview

The `test_agents.py` file integrates with the Mars simulation using a **hybrid autonomous system**:
- **Rule-based autopilot** for routine operations (fast, reliable)
- **AI agents** activated only during crisis situations (strategic, adaptive)

## Installation

```bash
cd hackathon
pip install strands-agents strands-agents-tools mcp boto3
```

## Hybrid Architecture

The system operates in three modes based on crisis level:

### 1. Normal Mode (Green ✅)
- Rule-based autopilot handles all operations
- Auto-harvest ready crops
- Auto-water plants when hydration < 80%
- No AI consultation needed
- Fast and efficient

### 2. Warning Mode (Yellow ⚠️)
- Rule-based autopilot continues operations
- AI agents on standby
- Consulted every 20 days for strategic advice
- Triggered by: food < 15 days, cognitive < 50%, micronutrient deficiency

### 3. Crisis Mode (Red 🚨)
- Rule-based autopilot handles immediate actions
- AI agents consulted every 10 days for complex decisions
- Triggered by: food < 5 days, plant wilting, astronaut hydration < 30%, water < 50L

## Usage

### Run with Slower Simulation (Recommended)

Start the simulation with 10-second delay per day:
```bash
# Terminal 1
cd hackathon/simulation
rm state.json
python -c "from sim import run; run(tick_delay=10.0)"
```

Start the hybrid autonomous system:
```bash
# Terminal 2
cd hackathon
python test_agents.py autonomous
```

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
Scans simulation and returns:
- List of issues (astronaut health, plant status, resources)
- Crisis level: "normal", "warning", or "critical"

### `execute_action(action, target)`
Executes actions on the simulation:
- `harvest` - Harvest a specific plant
- `water` - Water a specific plant
- `water_all` - Water all plants

### `run_autonomous_survival_management()`
Main hybrid control loop:
1. Checks simulation state every day
2. Executes rule-based actions immediately
3. Activates AI agents only during crises
4. Balances speed with intelligence

## Rule-Based Autopilot

The autopilot handles routine operations without AI:

**Harvest Rule**: Automatically harvest any plant that reaches maturity
- Radish: Day 25
- Herbs: Day 30
- Lettuce: Day 35
- Beans: Day 60
- Potato: Day 90

**Watering Rules**:
- Critical: Water individual plants if hydration < 40%
- Maintenance: Water all plants if any < 80%
- Frequency: Checks every simulation day

## AI Agent System

When crisis mode activates, the system uses a **Swarm multi-agent pattern**:

### Environment Agent
- Manages greenhouse conditions
- Optimizes plant health
- Controls water resources
- Handles environmental emergencies

### Nutrition Agent
- Monitors crew health metrics
- Optimizes food production
- Manages nutritional balance
- Handles medical emergencies

Agents collaborate through handoffs to make holistic survival decisions.

## Example Output

```
--- Day 25 Check ---
Crew: 4/4 | Food: 0 kcal | Water: 850L
Found 1 issue(s) | Crisis Level: NORMAL
  • ACTION: Radish ready for harvest (2.1 kg)

🤖 Autonomous actions:
  🌾 Harvested 2.10 kg of Radish
  💧 Watered all plants

--- Day 35 Check ---
Crew: 4/4 | Food: 1250 kcal | Water: 750L
Found 2 issue(s) | Crisis Level: WARNING
  • WARNING: 3.5 days of food remaining
  • ACTION: Lettuce ready for harvest (4.3 kg)

🤖 Autonomous actions:
  🌾 Harvested 4.30 kg of Lettuce
  💧 Watered all plants

⚠️  Warning level - AI agents on standby

--- Day 45 Check ---
Crew: 4/4 | Food: 450 kcal | Water: 650L
Found 3 issue(s) | Crisis Level: CRITICAL
  • CRITICAL: Only 1.2 days of food remaining
  • WARNING: Alex cognitive performance at 45%
  • WARNING: Jordan micronutrient score at 55%

🤖 Autonomous actions:
  💧 Watered all plants

🚨 CRISIS MODE ACTIVATED - Consulting AI agents...

🧠 AI Strategy: Immediate priority is accelerating bean harvest (Day 60) 
for protein. Maintain current watering schedule. Consider emergency 
rationing to extend food supply until next harvest...
```

## Configuration

### Performance Modes

**Fast Mode (Recommended for demos):**
```python
# In test_agents.py:
AI_ENABLED = True
AI_CRISIS_ONLY = True
AI_CONSULTATION_INTERVAL = 20
MODEL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"  # Fast & cheap
```

**Pure Algorithm Mode (Fastest, $0 cost):**
```python
AI_ENABLED = False  # No AI calls, pure mathematics
```

**Full AI Mode (Slowest, most intelligent):**
```python
AI_ENABLED = True
AI_CRISIS_ONLY = False
AI_CONSULTATION_INTERVAL = 1
MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Smartest
```

See `OPTIMIZATION_GUIDE.md` for detailed performance comparison.

Edit these variables in `test_agents.py`:
- `check_interval_days`: How often to check (default: 1 day, but checks every day regardless)
- `max_days`: When to stop monitoring (default: 450 days)
- `tick_delay` in sim.py: Simulation speed (default: 3s, recommended: 10s)
- Crisis consultation frequency: Every 10 days (critical) or 20 days (warning)

## Why Hybrid?

**Rule-based autopilot**:
- ✅ Fast response (< 1 second)
- ✅ Reliable and predictable
- ✅ No API costs
- ✅ Handles 90% of operations

**AI agents**:
- ✅ Strategic thinking
- ✅ Adapts to novel situations
- ✅ Provides explanations
- ⚠️ Slower (5-30 seconds)
- ⚠️ API costs

The hybrid approach gives you the best of both worlds: fast routine operations with intelligent crisis management.

## Troubleshooting

### Astronauts still dying?
- Increase simulation `tick_delay` to 10+ seconds
- Check that agents are harvesting (look for 🌾 messages)
- Verify food inventory is increasing after harvests

### Agents too slow?
- Reduce AI consultation frequency (change `% 10` to `% 20`)
- Disable crisis mode entirely for pure rule-based operation

### Plants wilting?
- Check water supply isn't depleted
- Verify watering actions are executing (look for 💧 messages)
- Reduce simulation speed if agents can't keep up
