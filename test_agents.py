"""
Test script for Mars Greenhouse agents using Swarm multi-agent pattern.

Usage:
    cd amazon-bedrock-agentcore-samples/use-cases/mars-greenhouse
    .venv/bin/python test_agents.py
"""
import json
import asyncio
import os
import sys

# Add simulation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "simulation"))
from sim import load_state, save_state, SimState

os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

MCP_URL = "https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"
MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


# ── Simulation Integration Functions ──────────────────────────────────────────

def get_simulation_state() -> dict:
    """Get current simulation state for agent decision-making."""
    state = load_state()
    
    astronauts_summary = []
    for a in state.astronauts:
        astronauts_summary.append({
            "name": a.name,
            "alive": a.isAlive,
            "hydration": round(a.hydrationLevel, 2),
            "cognitive": round(a.cognitivePerformance, 2),
            "bone_health": round(a.boneHealthScore, 2),
            "immune": round(a.immuneScore, 2),
            "micronutrient_score": round(a.micronutrientScore, 2),
            "calorie_deficit_days": round(a.calorieDeficitAccumulated / a.dailyCalorieNeed, 1),
            "emergency_food_days": round(a.storedFoodCalories / a.dailyCalorieNeed, 1),
        })

    plants_summary = []
    for p in state.plants:
        plants_summary.append({
            "name": p.name,
            "stage": p.get_growth_stage(),
            "hydration": round(p.hydration, 1),
            "days_planted": p.days_planted,
            "growth_cycle": p.growth_cycle_days,
            "harvestable": p.is_harvestable(),
            "expected_yield_kg": round(p.harvest_kg(), 2) if p.is_harvestable() else 0,
        })

    inventory_summary = {
        "Potato": round(state.inventory.Potato, 2),
        "Lettuce": round(state.inventory.Lettuce, 2),
        "Radish": round(state.inventory.Radish, 2),
        "Beans": round(state.inventory.Beans, 2),
        "Herbs": round(state.inventory.Herbs, 2),
        "total_kg": round(state.inventory.total_kg(), 2),
        "total_kcal": round(state.inventory.total_kcal(), 0),
    }

    return {
        "day": state.day,
        "astronauts": astronauts_summary,
        "plants": plants_summary,
        "inventory": inventory_summary,
        "resources": {
            "water_liters": round(state.resources.water_liters, 1),
            "growing_area_m2": round(state.resources.growing_area_m2, 1),
            "energy_kwh": round(state.resources.energy_kwh, 1),
        }
    }


def execute_action(action: str, target: str = None) -> dict:
    """Execute an action on the simulation based on agent decision."""
    state = load_state()
    
    if action == "harvest":
        for plant in state.plants:
            if plant.name == target and plant.is_harvestable():
                kg = plant.harvest_kg()
                current = getattr(state.inventory, plant.name, 0.0)
                setattr(state.inventory, plant.name, round(current + kg, 3))
                plant.days_planted = 0
                save_state(state)
                return {"success": True, "message": f"Harvested {kg:.2f} kg of {target}"}
        return {"success": False, "message": f"{target} not ready for harvest"}
    
    elif action == "water":
        for plant in state.plants:
            if plant.name == target:
                water_needed = plant.count * 0.5
                if state.resources.water_liters >= water_needed:
                    state.resources.water_liters -= water_needed
                    plant.hydration = min(100.0, plant.hydration + 10.0)
                    save_state(state)
                    return {"success": True, "message": f"Watered {target}"}
                return {"success": False, "message": "Not enough water"}
        return {"success": False, "message": f"Plant {target} not found"}
    
    elif action == "water_all":
        for plant in state.plants:
            water_needed = plant.count * 0.5
            if state.resources.water_liters >= water_needed:
                state.resources.water_liters -= water_needed
                plant.hydration = min(100.0, plant.hydration + 10.0)
        save_state(state)
        return {"success": True, "message": "Watered all plants"}
    
    else:
        return {"success": False, "message": f"Unknown action: {action}"}


def analyze_critical_issues() -> list:
    """Analyze simulation state and identify critical issues requiring agent intervention."""
    state = load_state()
    issues = []
    
    # Check astronaut health
    for a in state.astronauts:
        if not a.isAlive:
            continue
        if a.hydrationLevel < 0.3:
            issues.append(f"CRITICAL: {a.name} hydration at {a.hydrationLevel*100:.0f}%")
        if a.cognitivePerformance < 0.5:
            issues.append(f"WARNING: {a.name} cognitive performance at {a.cognitivePerformance*100:.0f}%")
        if a.calorieDeficitAccumulated / a.dailyCalorieNeed > 10:
            issues.append(f"WARNING: {a.name} has {a.calorieDeficitAccumulated/a.dailyCalorieNeed:.1f} days calorie deficit")
        if a.micronutrientScore < 0.6:
            issues.append(f"WARNING: {a.name} micronutrient score at {a.micronutrientScore*100:.0f}%")
    
    # Check plant health
    for p in state.plants:
        if p.hydration < 20:
            issues.append(f"CRITICAL: {p.name} wilting (hydration {p.hydration:.0f}%)")
        elif p.hydration < 40:
            issues.append(f"WARNING: {p.name} low hydration ({p.hydration:.0f}%)")
        if p.is_harvestable():
            issues.append(f"ACTION: {p.name} ready for harvest ({p.harvest_kg():.1f} kg)")
    
    # Check food supply
    alive_count = sum(1 for a in state.astronauts if a.isAlive)
    if alive_count > 0:
        total_kcal = state.inventory.total_kcal()
        days_left = total_kcal / (3000 * alive_count)
        if days_left < 5:
            issues.append(f"CRITICAL: Only {days_left:.1f} days of food remaining")
        elif days_left < 15:
            issues.append(f"WARNING: {days_left:.1f} days of food remaining")
    
    # Check water
    if state.resources.water_liters < 50:
        issues.append(f"CRITICAL: Water supply at {state.resources.water_liters:.0f}L")
    elif state.resources.water_liters < 200:
        issues.append(f"WARNING: Water supply at {state.resources.water_liters:.0f}L")
    
    return issues


# ── 1. Swarm Multi-Agent System ───────────────────────────────────────────────
def test_greenhouse_swarm():
    from strands import Agent
    from strands.multiagent.swarm import Swarm
    from strands.tools.mcp import MCPClient
    from mcp.client.streamable_http import streamablehttp_client

    print("\n=== Mars Greenhouse Swarm (Multi-Agent Collaboration) ===")

    mcp_client = MCPClient(lambda: streamablehttp_client(MCP_URL))

    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()
        print(f"Loaded {len(mcp_tools)} MCP tool(s)")

        # Create specialized agents
        environment_agent = Agent(
            name="environment_agent",
            model=MODEL,
            tools=mcp_tools,
            description="Specializes in greenhouse conditions, plant stress, and environmental control",
            system_prompt=(
                "You are the Mars Greenhouse Environment Agent. "
                "Use the knowledge base to answer questions about greenhouse conditions, "
                "plant stress, and environmental control for a Mars mission. "
                "If the question involves nutrition or crop planning, hand off to the nutrition_agent."
            ),
        )

        nutrition_agent = Agent(
            name="nutrition_agent",
            model=MODEL,
            tools=mcp_tools,
            description="Specializes in crop selection, planting schedules, and nutritional optimization",
            system_prompt=(
                "You are the Mars Greenhouse Nutrition Agent. "
                "Use the knowledge base to optimize crop selection and planting schedules "
                "for maximum nutritional output for 4 astronauts over 450 days. "
                "If the question involves environmental issues or plant stress, hand off to the environment_agent."
            ),
        )

        # Create swarm with both agents
        swarm = Swarm(
            nodes=[environment_agent, nutrition_agent],
            entry_point=environment_agent,
            max_handoffs=10,
            max_iterations=15
        )

        # Test 1: Environment-focused query
        print("\n--- Test 1: Environment Issue ---")
        result = swarm(
            "It is day 15 of the mission. Temperature is 26°C and lettuce is showing "
            "leaf tip burn. What is the likely cause and what should I do?"
        )
        print(f"Status: {result.status}")
        print(f"Agents involved: {[node.node_id for node in result.node_history]}")
        print(f"Response: {result.results}")

        # Test 2: Nutrition-focused query
        print("\n--- Test 2: Nutrition Planning ---")
        result = swarm(
            "We are on day 30. We have lettuce, radish, and spinach growing. "
            "Are we meeting the protein requirements for 4 astronauts? "
            "What crops should we plant next to fill any gaps?"
        )
        print(f"Status: {result.status}")
        print(f"Agents involved: {[node.node_id for node in result.node_history]}")
        print(f"Response: {result.results}")

        # Test 3: Complex query requiring both agents
        print("\n--- Test 3: Complex Multi-Agent Query ---")
        result = swarm(
            "Day 45: We're experiencing high humidity (85%) and need to adjust our crop plan. "
            "Which crops are most affected by this humidity? Should we change our planting schedule "
            "to maintain nutritional targets for the crew?"
        )
        print(f"Status: {result.status}")
        print(f"Agents involved: {[node.node_id for node in result.node_history]}")
        print(f"Handoffs: {len(result.node_history) - 1}")
        print(f"Response: {result.results}")


# ── 2. Individual Environment Agent (for comparison) ──────────────────────────
def test_environment_agent():
    from strands import Agent
    from strands.tools.mcp import MCPClient
    from mcp.client.streamable_http import streamablehttp_client

    print("\n=== 2. Environment Agent (Standalone) ===")

    mcp_client = MCPClient(lambda: streamablehttp_client(MCP_URL))

    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()
        print(f"Loaded {len(mcp_tools)} MCP tool(s)")

        agent = Agent(
            model=MODEL,
            tools=mcp_tools,
            system_prompt=(
                "You are the Mars Greenhouse Environment Agent. "
                "Use the knowledge base to answer questions about greenhouse conditions, "
                "plant stress, and environmental control for a Mars mission."
            ),
        )

        response = agent(
            "It is day 15 of the mission. Temperature is 26°C and lettuce is showing "
            "leaf tip burn. What is the likely cause and what should I do?"
        )
        print("\nResponse:")
        print(response)


# ── 3. Individual Nutrition Agent (for comparison) ────────────────────────────
def test_nutrition_agent():
    from strands import Agent
    from strands.tools.mcp import MCPClient
    from mcp.client.streamable_http import streamablehttp_client

    print("\n=== 3. Nutrition Agent (Standalone) ===")

    mcp_client = MCPClient(lambda: streamablehttp_client(MCP_URL))

    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()
        print(f"Loaded {len(mcp_tools)} MCP tool(s)")

        agent = Agent(
            model=MODEL,
            tools=mcp_tools,
            system_prompt=(
                "You are the Mars Greenhouse Nutrition Agent. "
                "Use the knowledge base to optimize crop selection and planting schedules "
                "for maximum nutritional output for 4 astronauts over 450 days."
            ),
        )

        response = agent(
            "We are on day 30. We have lettuce, radish, and spinach growing. "
            "Are we meeting the protein requirements for 4 astronauts? "
            "What crops should we plant next to fill any gaps?"
        )
        print("\nResponse:")
        print(response)


# ── 4. Event Handler (prompt builder) ─────────────────────────────────────────
def test_event_handler():
    os.environ.setdefault("GREENHOUSE_COMMANDER_ARN", "arn:aws:bedrock:us-west-2:000000000000:agent-runtime/local-test")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "event_handler"))
    from lambda_function import build_prompt

    print("\n=== 4. Event Handler (prompt builder) ===")

    events = [
        ("dust_storm",        {"severity_pct": 60, "duration_hours": 72}),
        ("power_failure",     {"affected_systems": "lighting zone B", "available_pct": 65}),
        ("crew_health_alert", {"astronaut_id": "A2", "condition": "vitamin C deficiency symptoms"}),
        ("simulation_advance",{"days": 30, "target_day": 60}),
    ]

    for event_type, data in events:
        print(f"\n[{event_type}]")
        print(build_prompt(event_type, data))


# ── 5. Autonomous Survival Management ─────────────────────────────────────────
def run_autonomous_survival_management(check_interval_days: int = 1, max_days: int = 450):
    """
    Run agents autonomously to manage astronaut survival.
    Checks simulation state periodically and makes decisions.
    """
    from strands import Agent
    from strands.multiagent.swarm import Swarm
    from strands.tools.mcp import MCPClient
    from mcp.client.streamable_http import streamablehttp_client
    import time

    print("\n=== Autonomous Survival Management System ===")
    print(f"Monitoring simulation every {check_interval_days} day(s)")
    
    mcp_client = MCPClient(lambda: streamablehttp_client(MCP_URL))

    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()
        print(f"Loaded {len(mcp_tools)} MCP tool(s)")

        # Create specialized agents
        environment_agent = Agent(
            name="environment_agent",
            model=MODEL,
            tools=mcp_tools,
            description="Manages greenhouse conditions, plant health, and resource allocation",
            system_prompt=(
                "You are the Mars Greenhouse Environment Agent managing a life-critical system. "
                "Your role is to keep plants healthy, manage water resources, and ensure optimal growing conditions. "
                "Analyze the simulation state and recommend specific actions like watering plants or harvesting crops. "
                "If nutrition or crew health is the primary concern, hand off to the nutrition_agent."
            ),
        )

        nutrition_agent = Agent(
            name="nutrition_agent",
            model=MODEL,
            tools=mcp_tools,
            description="Monitors crew nutrition and optimizes food production",
            system_prompt=(
                "You are the Mars Greenhouse Nutrition Agent responsible for crew survival. "
                "Monitor astronaut health metrics, food inventory, and nutritional balance. "
                "Recommend harvest timing and crop prioritization to prevent malnutrition. "
                "If environmental issues are affecting food production, hand off to the environment_agent."
            ),
        )

        swarm = Swarm(
            nodes=[environment_agent, nutrition_agent],
            entry_point=environment_agent,
            max_handoffs=5,
            max_iterations=10
        )

        last_check_day = 0
        
        while True:
            state = load_state()
            
            # Check if simulation has ended
            if state.day >= max_days:
                print(f"\n=== Simulation Complete (Day {state.day}) ===")
                break
            
            alive_count = sum(1 for a in state.astronauts if a.isAlive)
            if alive_count == 0:
                print("\n=== MISSION FAILED: All astronauts deceased ===")
                break
            
            # Only check at intervals
            if state.day < last_check_day + check_interval_days:
                time.sleep(1)
                continue
            
            last_check_day = state.day
            
            print(f"\n--- Day {state.day} Check ---")
            
            # Get current state and issues
            sim_state = get_simulation_state()
            issues = analyze_critical_issues()
            
            if not issues:
                print("✓ All systems nominal")
                continue
            
            print(f"Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  • {issue}")
            
            # Build prompt for agents
            prompt = f"""Day {state.day} Status Report:

Astronauts: {alive_count}/4 alive
Food Supply: {sim_state['inventory']['total_kcal']:.0f} kcal ({sim_state['inventory']['total_kg']:.1f} kg)
Water: {sim_state['resources']['water_liters']:.0f} L

Critical Issues:
{chr(10).join(f"- {issue}" for issue in issues)}

Detailed State:
{json.dumps(sim_state, indent=2)}

What actions should we take immediately to ensure crew survival? Be specific about which plants to water or harvest."""

            # Get agent recommendations
            print("\nConsulting agents...")
            result = swarm(prompt)
            
            print(f"\nAgent Response ({result.status}):")
            print(result.results)
            
            # Parse and execute recommended actions
            response_text = str(result.results).lower()
            
            # Auto-execute critical actions
            if "harvest" in response_text:
                for plant_name in ["Potato", "Lettuce", "Radish", "Beans", "Herbs"]:
                    if plant_name.lower() in response_text:
                        result = execute_action("harvest", plant_name)
                        if result["success"]:
                            print(f"✓ {result['message']}")
            
            if "water" in response_text:
                if "all" in response_text:
                    result = execute_action("water_all")
                    print(f"✓ {result['message']}")
                else:
                    for plant_name in ["Potato", "Lettuce", "Radish", "Beans", "Herbs"]:
                        if plant_name.lower() in response_text:
                            result = execute_action("water", plant_name)
                            if result["success"]:
                                print(f"✓ {result['message']}")
            
            time.sleep(2)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "autonomous":
        # Run autonomous management mode
        run_autonomous_survival_management(check_interval_days=1, max_days=450)
    else:
        # Run original tests
        test_greenhouse_swarm()
        test_environment_agent()
        test_nutrition_agent()
        test_event_handler()