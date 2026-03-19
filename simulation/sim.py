import time
import json
import os
from dataclasses import dataclass, asdict

@dataclass
class Astronaut:
    name: str
    health: float = 100.0
    hunger: float = 100.0  # 100 = full, 0 = starving
    mental_health: float = 100.0  # 100 = excellent, 0 = critical

@dataclass
class Plant:
    name: str
    count: int = 1  # Number of plants of this type
    hydration: float = 100.0  # 100 = fully hydrated, 0 = dead
    days_planted: int = 0  # Days since planting
    growth_cycle_days: int = 30  # Total days to maturity
    
    def get_growth_stage(self) -> str:
        """Returns: seedling, vegetative, mature, or wilting"""
        if self.hydration < 20.0:
            return "wilting"
        
        progress = self.days_planted / self.growth_cycle_days
        if progress < 0.25:
            return "seedling"
        elif progress < 0.75:
            return "vegetative"
        else:
            return "mature"

@dataclass
class Resources:
    water_liters: float = 1000.0  # Total water available
    growing_area_m2: float = 50.0  # Total growing area in m²
    energy_kwh: float = 500.0  # Energy storage in kWh

@dataclass
class SimState:
    day: int = 0
    astronauts: list = None
    plants: list = None
    resources: Resources = None

    def __post_init__(self):
        if self.astronauts is None:
            self.astronauts = [
                Astronaut("Alex"),
                Astronaut("Jordan"),
                Astronaut("Sam"),
                Astronaut("Riley"),
            ]
        if self.plants is None:
            self.plants = [
                Plant("Potato", count=10, growth_cycle_days=90),
                Plant("Lettuce", count=15, growth_cycle_days=35),
                Plant("Radish", count=20, growth_cycle_days=25),
                Plant("Beans", count=8, growth_cycle_days=60),
                Plant("Herbs", count=5, growth_cycle_days=30),
            ]
        if self.resources is None:
            self.resources = Resources()

    def tick(self):
        self.day += 1
        
        # Update plant hydration and growth
        for plant in self.plants:
            plant.hydration = max(0.0, plant.hydration - 2.0)
            plant.days_planted += 1
        
        # Update astronauts
        for a in self.astronauts:
            a.hunger = max(0.0, a.hunger - 5.0)
            
            # Feed astronauts if plants are healthy and mature
            mature_plants = [p for p in self.plants if p.hydration > 20.0 and p.get_growth_stage() == "mature"]
            if mature_plants and a.hunger < 80.0:
                a.hunger = min(100.0, a.hunger + 15.0)
            
            # Health degrades if hungry
            if a.hunger < 20.0:
                a.health = max(0.0, a.health - 3.0)
            else:
                a.health = min(100.0, a.health + 0.5)
            
            # Mental health degrades slowly over time
            a.mental_health = max(0.0, a.mental_health - 0.5)
            
            # Mental health improves with variety of plants (herbs help morale)
            herbs_alive = any(p.name == "Herbs" and p.hydration > 20.0 for p in self.plants)
            if herbs_alive:
                a.mental_health = min(100.0, a.mental_health + 0.3)

    def to_dict(self):
        return {
            "day": self.day,
            "astronauts": [asdict(a) for a in self.astronauts],
            "plants": [asdict(p) for p in self.plants],
            "resources": asdict(self.resources),
        }

BASE = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE, "state.json")
CONTROL_FILE = os.path.join(BASE, "control.json")

def save_state(state: SimState):
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_dict(), f)

def load_state() -> SimState:
    if not os.path.exists(STATE_FILE):
        return SimState()
    with open(STATE_FILE) as f:
        data = json.load(f)
    state = SimState(day=data["day"])
    state.astronauts = [Astronaut(**a) for a in data["astronauts"]]
    state.plants = [Plant(**p) for p in data["plants"]]
    state.resources = Resources(**data["resources"])
    return state

def read_control() -> dict:
    if not os.path.exists(CONTROL_FILE):
        return {"paused": False, "reset": False, "hydrate": False, "plant_index": -1}
    with open(CONTROL_FILE) as f:
        return json.load(f)

def write_control(paused: bool, reset: bool = False, hydrate: bool = False, plant_index: int = -1):
    with open(CONTROL_FILE, "w") as f:
        json.dump({"paused": paused, "reset": reset, "hydrate": hydrate, "plant_index": plant_index}, f)

def run(days: int = 450, tick_delay: float = 0.5):
    write_control(paused=False)
    state = load_state()
    print(f"Starting from day {state.day}")

    while state.day < days:
        ctrl = read_control()

        if ctrl.get("reset"):
            state = SimState()
            save_state(state)
            write_control(paused=ctrl.get("paused", False), reset=False)
            print("Simulation reset to day 0")
            continue

        if ctrl.get("hydrate"):
            # Hydrate specific plant or all plants
            plant_index = ctrl.get("plant_index", -1)
            if plant_index >= 0 and plant_index < len(state.plants):
                # Hydrate specific plant
                plant = state.plants[plant_index]
                water_needed = plant.count * 0.5
                if state.resources.water_liters >= water_needed:
                    state.resources.water_liters -= water_needed
                    plant.hydration = min(100.0, plant.hydration + 10.0)
                    print(f"Hydrated {plant.name}! Used {water_needed}L water")
                else:
                    print(f"Not enough water! Need {water_needed}L, have {state.resources.water_liters:.1f}L")
            else:
                # Hydrate all plants
                water_needed = sum(p.count * 0.5 for p in state.plants)
                if state.resources.water_liters >= water_needed:
                    state.resources.water_liters -= water_needed
                    for plant in state.plants:
                        plant.hydration = min(100.0, plant.hydration + 10.0)
                    print(f"Hydrated all plants! Used {water_needed}L water")
                else:
                    print(f"Not enough water! Need {water_needed}L, have {state.resources.water_liters:.1f}L")
            save_state(state)
            write_control(paused=ctrl.get("paused", False), reset=False, hydrate=False, plant_index=-1)
            continue

        if ctrl.get("paused"):
            time.sleep(0.2)
            continue

        state.tick()
        save_state(state)
        plant_status = " | ".join([f"{p.name}: {p.hydration:.1f}" for p in state.plants])
        print(f"Day {state.day} | {plant_status}")
        time.sleep(tick_delay)

    print("Simulation complete.")

if __name__ == "__main__":
    run()
