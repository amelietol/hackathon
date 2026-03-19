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
import time

# Add simulation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "simulation"))
from sim import load_state, save_state, SimState
from resource_optimizer import calculate_optimal_watering, calculate_optimal_rationing, calculate_harvest_priority

os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

MCP_URL = "https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"
# Use Claude Haiku - 3x faster and 10x cheaper than Sonnet
MODEL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"  # Fast model for real-time decisions
# MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Slower but smarter - use for complex planning

# AI Configuration
AI_ENABLED = True  # Set to False to run pure rule-based (fastest)
AI_CONSULTATION_INTERVAL = 20  # Only consult AI every N days (not every day)
AI_CRISIS_ONLY = True  # Only use AI during crisis mode


# ── Simulation Integration Functions ──────────────────────────────────────────

def get_simulation_state() -> dict:
    """Get current simulation state for agent decision-making."""
    state = load_state()
    
    astronauts_summary = []
    total_emergency_rations = 0
    for a in state.astronauts:
        if a.isAlive:
            total_emergency_rations += a.storedFoodCalories
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
            "emergency_food_kcal": round(a.storedFoodCalories, 0),
        })

    plants_summary = []
    for p in state.plants:
        plants_summary.append({
            "plant_id": p.plant_id,
            "name": p.name,
            "area_m2": p.area_m2,
            "stage": p.get_growth_stage(),
            "hydration": round(p.hydration, 1),
            "days_planted": p.days_planted,
            "growth_cycle": p.growth_cycle_days,
            "harvestable": p.is_harvestable(),
            "expected_yield_kg": round(p.harvest_kg(), 2) if p.is_harvestable() else 0,
        })

    greenhouse_kcal = round(state.inventory.total_kcal(), 0)
    total_food_kcal = greenhouse_kcal + total_emergency_rations
    
    inventory_summary = {
        "Potato": round(state.inventory.Potato, 2),
        "Lettuce": round(state.inventory.Lettuce, 2),
        "Radish": round(state.inventory.Radish, 2),
        "Beans": round(state.inventory.Beans, 2),
        "Herbs": round(state.inventory.Herbs, 2),
        "total_kg": round(state.inventory.total_kg(), 2),
        "greenhouse_kcal": greenhouse_kcal,
        "emergency_rations_kcal": round(total_emergency_rations, 0),
        "total_kcal": total_food_kcal,
    }

    return {
        "day": state.day,
        "astronauts": astronauts_summary,
        "plants": plants_summary,
        "inventory": inventory_summary,
        "resources": {
            "water_liters": round(state.resources.water_liters, 1),
            "growing_area_m2": round(state.resources.growing_area_m2, 1),
            "growing_area_used": round(sum(p.area_m2 for p in state.plants), 1),
            "growing_area_available": round(state.resources.available_growing_area(state.plants), 1),
            "energy_kwh": round(state.resources.energy_kwh, 1),
        }
    }


def execute_action(action: str, target: str = None, amount: float = None, **kwargs) -> dict:
    """Execute an action on the simulation based on agent decision."""
    from sim import read_control, write_control
    
    # Pause simulation to prevent race conditions
    ctrl = read_control()
    was_paused = ctrl.get("paused", False)
    if not was_paused:
        write_control(paused=True)
        time.sleep(0.2)  # Wait for simulation to pause
    
    try:
        state = load_state()
        result = None
        
        if action == "plant":
            # Plant a new crop - only allow if there's available space
            crop_name = target
            area = amount if amount else 5.0  # Default 5m²
            
            # Check if there's enough space
            available = state.resources.available_growing_area(state.plants)
            if area > available:
                result = {"success": False, "message": f"Not enough space. Available: {available:.1f}m², Requested: {area:.1f}m²"}
            else:
                result = state.plant_crop(crop_name, area)
                if result["success"]:
                    save_state(state)
                    time.sleep(0.1)  # Ensure write completes
                    print(f"    DEBUG: Planted {crop_name}, total plants now: {len(state.plants)}")
        
        elif action == "remove_plant":
            # DISABLED: Plants cannot be removed once planted
            result = {"success": False, "message": "Cannot remove plants - they are permanent once planted"}
        
        elif action == "harvest":
            for plant in state.plants:
                if plant.name == target and plant.is_harvestable():
                    kg = plant.harvest_kg()
                    current = getattr(state.inventory, plant.name, 0.0)
                    setattr(state.inventory, plant.name, round(current + kg, 3))
                    # Reset plant to start new growth cycle (plants are permanent)
                    plant.days_planted = 0
                    plant.hydration = 100.0  # Reset hydration after harvest
                    save_state(state)
                    result = {"success": True, "message": f"Harvested {kg:.2f} kg of {target}, plant will regrow"}
                    break
            if result is None:
                result = {"success": False, "message": f"{target} not ready for harvest"}
        
        elif action == "water":
            for plant in state.plants:
                if plant.name == target or plant.plant_id == target:
                    water_amount = amount if amount else plant.water_needed_per_day()
                    if state.resources.water_liters >= water_amount:
                        state.resources.water_liters -= water_amount
                        # Calculate hydration increase based on water amount
                        # Base: daily need gives +20% hydration
                        hydration_increase = (water_amount / plant.water_needed_per_day()) * 20.0
                        plant.hydration = min(100.0, plant.hydration + hydration_increase)
                        save_state(state)
                        result = {"success": True, "message": f"Watered {plant.name} with {water_amount:.1f}L (+{hydration_increase:.0f}%)"}
                        break
                    result = {"success": False, "message": "Not enough water"}
                    break
            if result is None:
                result = {"success": False, "message": f"Plant {target} not found"}
        
        elif action == "water_all":
            total_water_used = 0
            for plant in state.plants:
                water_amount = amount if amount else plant.water_needed_per_day()
                if state.resources.water_liters >= water_amount:
                    state.resources.water_liters -= water_amount
                    total_water_used += water_amount
                    hydration_increase = (water_amount / plant.water_needed_per_day()) * 20.0
                    plant.hydration = min(100.0, plant.hydration + hydration_increase)
            save_state(state)
            result = {"success": True, "message": f"Watered all plants ({total_water_used:.1f}L used)"}
        
        elif action == "smart_water":
            # Use the optimization algorithm
            sim_state = get_simulation_state()
            if not sim_state['plants']:
                result = {"success": True, "message": "No plants to water"}
            else:
                watering_plans = calculate_optimal_watering(
                    sim_state['plants'],
                    state.resources.water_liters,
                    days_to_next_resupply=30
                )
                
                actions_taken = []
                for plan in watering_plans:
                    for plant in state.plants:
                        if plant.name == plan.plant_name:
                            if state.resources.water_liters >= plan.water_amount_liters:
                                state.resources.water_liters -= plan.water_amount_liters
                                hydration_increase = (plan.water_amount_liters / plant.water_needed_per_day()) * 20.0
                                plant.hydration = min(100.0, plant.hydration + hydration_increase)
                                actions_taken.append(f"{plan.plant_name}: {plan.water_amount_liters:.1f}L ({plan.reason})")
                
                save_state(state)
                result = {"success": True, "message": f"Smart watering: {'; '.join(actions_taken) if actions_taken else 'No watering needed'}"}
        
        else:
            result = {"success": False, "message": f"Unknown action: {action}"}
        
        return result
    
    finally:
        # Resume simulation if it wasn't paused before
        if not was_paused:
            time.sleep(0.1)  # Small delay to ensure state is fully written
            write_control(paused=False)


def analyze_critical_issues() -> list:
    """Analyze simulation state and identify critical issues requiring agent intervention."""
    state = load_state()
    issues = []
    crisis_level = "normal"  # normal, warning, critical
    
    # Check astronaut health
    for a in state.astronauts:
        if not a.isAlive:
            continue
        if a.hydrationLevel < 0.3:
            issues.append(f"CRITICAL: {a.name} hydration at {a.hydrationLevel*100:.0f}%")
            crisis_level = "critical"
        if a.cognitivePerformance < 0.5:
            issues.append(f"WARNING: {a.name} cognitive performance at {a.cognitivePerformance*100:.0f}%")
            if crisis_level == "normal":
                crisis_level = "warning"
        if a.calorieDeficitAccumulated / a.dailyCalorieNeed > 10:
            issues.append(f"WARNING: {a.name} has {a.calorieDeficitAccumulated/a.dailyCalorieNeed:.1f} days calorie deficit")
            if crisis_level == "normal":
                crisis_level = "warning"
        if a.micronutrientScore < 0.6:
            issues.append(f"WARNING: {a.name} micronutrient score at {a.micronutrientScore*100:.0f}%")
            if crisis_level == "normal":
                crisis_level = "warning"
    
    # Check plant health
    for p in state.plants:
        if p.hydration < 20:
            issues.append(f"CRITICAL: {p.name} wilting (hydration {p.hydration:.0f}%)")
            crisis_level = "critical"
        elif p.hydration < 40:
            issues.append(f"WARNING: {p.name} low hydration ({p.hydration:.0f}%)")
        if p.is_harvestable():
            issues.append(f"ACTION: {p.name} ready for harvest ({p.harvest_kg():.1f} kg)")
    
    # Check food supply
    alive_count = sum(1 for a in state.astronauts if a.isAlive)
    if alive_count > 0:
        greenhouse_kcal = state.inventory.total_kcal()
        emergency_kcal = sum(a.storedFoodCalories for a in state.astronauts if a.isAlive)
        total_kcal = greenhouse_kcal + emergency_kcal
        days_left = total_kcal / (3000 * alive_count)
        if days_left < 5:
            issues.append(f"CRITICAL: Only {days_left:.1f} days of food remaining")
            crisis_level = "critical"
        elif days_left < 15:
            issues.append(f"WARNING: {days_left:.1f} days of food remaining")
            if crisis_level == "normal":
                crisis_level = "warning"
    
    # Check water
    if state.resources.water_liters < 50:
        issues.append(f"CRITICAL: Water supply at {state.resources.water_liters:.0f}L")
        crisis_level = "critical"
    elif state.resources.water_liters < 200:
        issues.append(f"WARNING: Water supply at {state.resources.water_liters:.0f}L")
    
    return issues, crisis_level


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
            try:
                state = load_state()
            except (json.JSONDecodeError, FileNotFoundError):
                # State file is being written or doesn't exist yet
                time.sleep(0.2)
                continue
            
            # Check if simulation has ended
            if state.day >= max_days:
                print(f"\n=== Simulation Complete (Day {state.day}) ===")
                break
            
            alive_count = sum(1 for a in state.astronauts if a.isAlive)
            if alive_count == 0:
                print("\n=== MISSION FAILED: All astronauts deceased ===")
                break
            
            # Check every day (removed the interval check that was causing gaps)
            if state.day <= last_check_day:
                time.sleep(0.5)
                continue
            
            last_check_day = state.day
            
            # Get current state and issues
            sim_state = get_simulation_state()
            issues, crisis_level = analyze_critical_issues()
            
            # Check if plants exist - simulation handles initial planting on day 0
            if len(sim_state['plants']) == 0:
                print(f"\n⚠️ Day {state.day}: No plants in greenhouse!")
                print(f"   Note: Initial planting should happen automatically in simulation on day 0")
                print(f"   If this persists, there may be a state persistence issue")
                # Don't try to plant - let simulation handle it
                time.sleep(1.0)
                continue
            
            print(f"\n--- Day {state.day} Check ---")
            print(f"Crew: {alive_count}/4 | Food: {sim_state['inventory']['total_kcal']:.0f} kcal | Water: {sim_state['resources']['water_liters']:.0f}L | Growing: {sim_state['resources']['growing_area_used']:.0f}/{sim_state['resources']['growing_area_m2']:.0f}m²")
            
            if not issues:
                print("✓ All systems nominal")
                # Still water plants to maintain health
                result = execute_action("water_all")
                print(f"  {result['message']}")
                continue
            
            print(f"Found {len(issues)} issue(s) | Crisis Level: {crisis_level.upper()}")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  • {issue}")
            
            # Execute autonomous rule-based actions
            actions_taken = []
            
            # Rule 1: Use SMART WATERING algorithm
            result = execute_action("smart_water")
            if result["success"]:
                actions_taken.append(f"💧 {result['message']}")
            
            # Rule 2: Auto-harvest using priority algorithm
            sim_state = get_simulation_state()
            food_shortage = 1.0 - min(1.0, sim_state['inventory']['total_kcal'] / (12000 * 7))  # 7 days buffer
            harvest_priorities = calculate_harvest_priority(sim_state['plants'], food_shortage)
            
            for plant_name, priority, reason in harvest_priorities:
                if priority == 1:  # Urgent harvest
                    result = execute_action("harvest", plant_name)
                    if result["success"]:
                        actions_taken.append(f"🌾 {result['message']} - {reason}")
            
            if actions_taken:
                print("\n🤖 Autonomous actions:")
                for action in actions_taken:
                    print(f"  {action}")
            
            # AI CONSULTATION - Optimized for speed
            if AI_ENABLED and crisis_level == "critical":
                # Only consult AI during critical situations and at intervals
                if state.day % AI_CONSULTATION_INTERVAL == 0:
                    print("\n🚨 CRISIS - Consulting AI (brief)...")
                    
                    # Ultra-short prompt for speed
                    crisis_prompt = f"""Day {state.day}: {alive_count}/4 alive, {sim_state['inventory']['total_kcal']:.0f} kcal, {sim_state['resources']['water_liters']:.0f}L water. Critical: {issues[0] if issues else 'unknown'}. One sentence advice."""

                    try:
                        result = swarm(crisis_prompt)
                        response_text = str(result.results).strip().split('.')[0] + '.'
                        print(f"🧠 {response_text[:150]}")
                    except Exception as e:
                        print(f"⚠️  AI unavailable")
            
            elif AI_ENABLED and not AI_CRISIS_ONLY and crisis_level == "warning":
                # Optional: Brief check for warnings
                if state.day % (AI_CONSULTATION_INTERVAL * 2) == 0:
                    print(f"⚠️  AI: Monitoring {len(issues)} warnings")
            
            elif state.day % 20 == 0:
                # Status update without AI
                print(f"✅ Day {state.day}: All systems managed by algorithms")
            
            time.sleep(0.3)  # Reduced delay for faster response


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