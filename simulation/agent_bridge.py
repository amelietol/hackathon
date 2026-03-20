"""
Bridge between Mars simulation and AWS Bedrock Agent Core.
Allows the agent to read simulation state and issue commands.
"""
import json
import boto3
from typing import Optional
from sim import load_state, save_state, SimState

# Agent ARNs - load from environment or use defaults
import os
ENV_AGENT_ARN = os.getenv("ENV_AGENT_ARN", "arn:aws:bedrock-agentcore:us-west-2:610690630138:runtime/mars_environment_agent-90e0pIH7bS")
NUTRITION_AGENT_ARN = os.getenv("NUTRITION_AGENT_ARN", "arn:aws:bedrock-agentcore:us-west-2:610690630138:runtime/mars_nutrition_agent-vu7e2N4JEg")
REGION = os.getenv("AWS_REGION", "us-west-2")


class AgentBridge:
    def __init__(self, region: str = REGION):
        self.client = boto3.client("bedrock-agentcore", region_name=region)
        self.env_agent_arn = ENV_AGENT_ARN
        self.nutrition_agent_arn = NUTRITION_AGENT_ARN
        self.runtime_session_id = "mars-simulation-session-001-20240"  # min 33 chars

    def get_simulation_summary(self) -> dict:
        """Get current simulation state as a dict for the agent."""
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

    def send_to_environment_agent(self, prompt: str) -> dict:
        """
        Send environmental event to the environment agent.
        Example: "Dust storm incoming, severity 60%"
        """
        sim_state = self.get_simulation_summary()
        
        payload = {
            "prompt": prompt,
            "simulation_state": sim_state,
        }

        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.env_agent_arn,
                payload=json.dumps(payload),
                runtimeSessionId=self.runtime_session_id,
            )
            
            return {
                "success": True,
                "response": response,
                "simulation_state": sim_state,
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "simulation_state": sim_state,
            }

    def send_to_nutrition_agent(self, prompt: str) -> dict:
        """
        Send nutrition query to the nutrition agent.
        Example: "Astronaut Alex showing protein deficiency, recommend diet"
        """
        sim_state = self.get_simulation_summary()
        
        payload = {
            "prompt": prompt,
            "simulation_state": sim_state,
        }

        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.nutrition_agent_arn,
                payload=json.dumps(payload),
                runtimeSessionId=self.runtime_session_id,
            )
            
            return {
                "success": True,
                "response": response,
                "simulation_state": sim_state,
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "simulation_state": sim_state,
            }

    def execute_agent_command(self, command: dict) -> dict:
        """
        Execute a command from the agent on the simulation.
        
        Supported commands:
        - {"action": "harvest", "plant": "Potato"}
        - {"action": "water", "plant": "Lettuce"}
        - {"action": "water_all"}
        """
        state = load_state()
        action = command.get("action")
        
        if action == "harvest":
            plant_name = command.get("plant")
            for plant in state.plants:
                if plant.name == plant_name and plant.is_harvestable():
                    kg = plant.harvest_kg()
                    current = getattr(state.inventory, plant.name, 0.0)
                    setattr(state.inventory, plant.name, round(current + kg, 3))
                    plant.days_planted = 0
                    save_state(state)
                    return {"success": True, "message": f"Harvested {kg:.2f} kg of {plant_name}"}
            return {"success": False, "message": f"{plant_name} not ready for harvest"}
        
        elif action == "water":
            plant_name = command.get("plant")
            for plant in state.plants:
                if plant.name == plant_name:
                    water_needed = plant.count * 0.5
                    if state.resources.water_liters >= water_needed:
                        state.resources.water_liters -= water_needed
                        plant.hydration = min(100.0, plant.hydration + 10.0)
                        save_state(state)
                        return {"success": True, "message": f"Watered {plant_name}"}
                    return {"success": False, "message": "Not enough water"}
            return {"success": False, "message": f"Plant {plant_name} not found"}
        
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


# ── Example usage ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize bridge
    bridge = AgentBridge()
    
    # Get current state
    print("Current simulation state:")
    print(json.dumps(bridge.get_simulation_summary(), indent=2))
    
    # Send environmental event
    print("\n=== Sending to Environment Agent ===")
    response = bridge.send_to_environment_agent("Dust storm incoming, severity 60%")
    print(f"Success: {response['success']}")
    if response['success']:
        print(f"Response: {response['response']}")
    else:
        print(f"Error: {response['error']}")
    
    # Send nutrition query
    print("\n=== Sending to Nutrition Agent ===")
    response = bridge.send_to_nutrition_agent("Astronaut Alex showing protein deficiency")
    print(f"Success: {response['success']}")
    if response['success']:
        print(f"Response: {response['response']}")
    else:
        print(f"Error: {response['error']}")
    
    # Execute a command based on agent recommendation
    print("\n=== Executing Command ===")
    result = bridge.execute_agent_command({"action": "water_all"})
    print(f"Command result: {result}")
