import time
import json
import os
from dataclasses import dataclass, asdict

# ── Food nutrition tables ────────────────────────────────────────────────────
SPECIES_YIELD_KG_M2    = {"Potato": 6.0,  "Lettuce": 4.0, "Radish": 3.0, "Beans": 3.0,  "Herbs": 1.5}
SPECIES_HARVEST_INDEX  = {"Potato": 0.75, "Lettuce": 0.85,"Radish": 0.70,"Beans": 0.55, "Herbs": 0.80}
SPECIES_KCAL_PER_100G  = {"Potato": 77.0, "Lettuce": 15.0,"Radish": 16.0,"Beans": 100.0,"Herbs": 23.0}
SPECIES_PROTEIN_PER_100G = {"Potato": 2.0,"Lettuce": 1.4, "Radish": 0.7, "Beans": 7.0,  "Herbs": 3.2}

SPECIES_VIT_A_UG    = {"Potato": 0.0,  "Lettuce": 166.0,"Radish": 0.0,  "Beans": 0.0,  "Herbs": 264.0}
SPECIES_VIT_C_MG    = {"Potato": 19.7, "Lettuce": 9.2,  "Radish": 14.8, "Beans": 12.2, "Herbs": 18.0}
SPECIES_VIT_K_UG    = {"Potato": 0.0,  "Lettuce": 126.0,"Radish": 0.0,  "Beans": 0.0,  "Herbs": 415.0}
SPECIES_FOLATE_UG   = {"Potato": 15.0, "Lettuce": 38.0, "Radish": 25.0, "Beans": 130.0,"Herbs": 68.0}
SPECIES_POTASSIUM_MG= {"Potato": 421.0,"Lettuce": 194.0,"Radish": 233.0,"Beans": 405.0,"Herbs": 295.0}

BODY_MASS_KG          = 75.0
DAILY_CALORIE_NEED    = 3000.0
DAILY_PROTEIN_NEED_G  = 112.5
DAILY_WATER_NEED_L    = 2.3
DAILY_VIT_A_UG        = 900.0
DAILY_VIT_C_MG        = 90.0
DAILY_VIT_K_UG        = 120.0
DAILY_FOLATE_UG       = 400.0
DAILY_POTASSIUM_MG    = 4700.0


@dataclass
class Astronaut:
    id: str
    name: str
    bodyMassKg: float = BODY_MASS_KG
    dailyCalorieNeed: float   = DAILY_CALORIE_NEED
    dailyProteinNeedG: float  = DAILY_PROTEIN_NEED_G
    dailyWaterNeedL: float    = DAILY_WATER_NEED_L
    carbTargetPct: float    = 0.50
    proteinTargetPct: float = 0.175
    fatTargetPct: float     = 0.325
    vitaminA_ug: float    = DAILY_VIT_A_UG
    vitaminC_mg: float    = DAILY_VIT_C_MG
    vitaminK_ug: float    = DAILY_VIT_K_UG
    folate_ug: float      = DAILY_FOLATE_UG
    potassium_mg: float   = DAILY_POTASSIUM_MG
    calorieDeficitAccumulated: float  = 0.0
    proteinDeficitAccumulated: float  = 0.0
    hydrationLevel: float        = 1.0
    micronutrientScore: float    = 1.0
    cognitivePerformance: float  = 1.0
    boneHealthScore: float       = 1.0
    immuneScore: float           = 1.0
    isAlive: bool = True
    # Starting rations: 60 days supply (enough to reach first harvest + safety buffer)
    # 60 days × 3000 kcal/day = 180,000 kcal per astronaut
    storedFoodCalories: float  = 180000.0
    storedFoodProteinG: float  = 6750.0  # 60 days × 112.5g/day

    def tick(self, kcal_consumed: float, protein_consumed_g: float,
             water_consumed_l: float, vit_a: float, vit_c: float,
             vit_k: float, folate: float, potassium: float):
        if not self.isAlive:
            return
        cal_deficit = max(0.0, self.dailyCalorieNeed - kcal_consumed)
        cal_surplus = max(0.0, kcal_consumed - self.dailyCalorieNeed)
        self.calorieDeficitAccumulated = max(0.0, self.calorieDeficitAccumulated + cal_deficit - cal_surplus * 0.5)
        prot_deficit = max(0.0, self.dailyProteinNeedG - protein_consumed_g)
        self.proteinDeficitAccumulated = max(0.0, self.proteinDeficitAccumulated + prot_deficit)
        hydration_fraction = min(1.0, water_consumed_l / self.dailyWaterNeedL)
        self.hydrationLevel = max(0.0, min(1.0,
            self.hydrationLevel + (hydration_fraction - 0.5) * 0.1))
        scores = [
            min(1.0, vit_a    / self.vitaminA_ug)   if self.vitaminA_ug   > 0 else 1.0,
            min(1.0, vit_c    / self.vitaminC_mg)   if self.vitaminC_mg   > 0 else 1.0,
            min(1.0, vit_k    / self.vitaminK_ug)   if self.vitaminK_ug   > 0 else 1.0,
            min(1.0, folate   / self.folate_ug)     if self.folate_ug     > 0 else 1.0,
            min(1.0, potassium/ self.potassium_mg)  if self.potassium_mg  > 0 else 1.0,
        ]
        daily_micro = sum(scores) / len(scores)
        self.micronutrientScore = max(0.0, min(1.0,
            self.micronutrientScore * 0.95 + daily_micro * 0.05))
        cal_factor = max(0.0, 1.0 - self.calorieDeficitAccumulated / 30000.0)
        self.cognitivePerformance = max(0.0, min(1.0,
            cal_factor * 0.6 + self.micronutrientScore * 0.4))
        vit_k_score = min(1.0, vit_k / self.vitaminK_ug) if self.vitaminK_ug > 0 else 1.0
        self.boneHealthScore = max(0.0, min(1.0,
            self.boneHealthScore - (1.0 - vit_k_score) * 0.002))
        immune_inputs = [
            min(1.0, vit_a  / self.vitaminA_ug)  if self.vitaminA_ug  > 0 else 1.0,
            min(1.0, vit_c  / self.vitaminC_mg)  if self.vitaminC_mg  > 0 else 1.0,
            min(1.0, folate / self.folate_ug)    if self.folate_ug    > 0 else 1.0,
        ]
        daily_immune = sum(immune_inputs) / len(immune_inputs)
        self.immuneScore = max(0.0, min(1.0,
            self.immuneScore * 0.97 + daily_immune * 0.03))
        if self.calorieDeficitAccumulated > 90000.0:
            self.isAlive = False
        if self.hydrationLevel < 0.05:
            self.isAlive = False


@dataclass
class Plant:
    name: str
    count: int = 1
    hydration: float = 100.0
    days_planted: int = 0
    growth_cycle_days: int = 30
    area_m2: float = 1.0

    def get_growth_stage(self) -> str:
        if self.hydration < 20.0:
            return "wilting"
        progress = self.days_planted / self.growth_cycle_days
        if progress < 0.25:   return "seedling"
        elif progress < 0.75: return "vegetative"
        else:                 return "mature"

    def is_harvestable(self) -> bool:
        return self.get_growth_stage() == "mature" and self.hydration >= 20.0

    def harvest_kg(self) -> float:
        if not self.is_harvestable():
            return 0.0
        health_factor = max(0.0, self.hydration / 100.0)
        return round(SPECIES_YIELD_KG_M2.get(self.name, 3.0)
                     * self.area_m2
                     * SPECIES_HARVEST_INDEX.get(self.name, 0.7)
                     * health_factor, 2)


@dataclass
class Inventory:
    Potato:  float = 0.0
    Lettuce: float = 0.0
    Radish:  float = 0.0
    Beans:   float = 0.0
    Herbs:   float = 0.0

    def total_kg(self) -> float:
        return sum(getattr(self, n) for n in SPECIES_KCAL_PER_100G)

    def total_kcal(self) -> float:
        return sum(getattr(self, n) * 10.0 * SPECIES_KCAL_PER_100G[n] for n in SPECIES_KCAL_PER_100G)

    def consume_for_astronauts(self, astronauts: list) -> dict:
        n = len([a for a in astronauts if a.isAlive])
        if n == 0:
            return {}
        total_kcal_needed   = sum(a.dailyCalorieNeed  for a in astronauts if a.isAlive)
        total_protein_needed= sum(a.dailyProteinNeedG for a in astronauts if a.isAlive)
        inv_kcal = self.total_kcal()
        fraction_from_inv = min(1.0, total_kcal_needed / inv_kcal) if inv_kcal > 0 else 0.0
        nutrients = {k: 0.0 for k in ["kcal","protein","vit_a","vit_c","vit_k","folate","potassium"]}
        for name in SPECIES_KCAL_PER_100G:
            kg = getattr(self, name, 0.0)
            consume_kg = kg * fraction_from_inv
            setattr(self, name, max(0.0, kg - consume_kg))
            per100 = consume_kg * 10.0
            nutrients["kcal"]      += per100 * SPECIES_KCAL_PER_100G[name]
            nutrients["protein"]   += per100 * SPECIES_PROTEIN_PER_100G[name]
            nutrients["vit_a"]     += per100 * SPECIES_VIT_A_UG[name]
            nutrients["vit_c"]     += per100 * SPECIES_VIT_C_MG[name]
            nutrients["vit_k"]     += per100 * SPECIES_VIT_K_UG[name]
            nutrients["folate"]    += per100 * SPECIES_FOLATE_UG[name]
            nutrients["potassium"] += per100 * SPECIES_POTASSIUM_MG[name]
        remaining_kcal = max(0.0, total_kcal_needed - nutrients["kcal"])
        for a in astronauts:
            if not a.isAlive: continue
            share = remaining_kcal / n
            if a.storedFoodCalories >= share:
                a.storedFoodCalories -= share
                nutrients["kcal"] += share
                prot_share = min(a.storedFoodProteinG, a.dailyProteinNeedG)
                a.storedFoodProteinG = max(0.0, a.storedFoodProteinG - prot_share)
                nutrients["protein"] += prot_share
        return {k: v / n for k, v in nutrients.items()}


@dataclass
class Resources:
    water_liters: float    = 1000.0
    growing_area_m2: float = 50.0
    energy_kwh: float      = 500.0


@dataclass
class SimState:
    day: int = 0
    astronauts: list = None
    plants: list = None
    resources: Resources = None
    inventory: Inventory = None

    def __post_init__(self):
        if self.astronauts is None:
            self.astronauts = [
                Astronaut(id="a1", name="Alex"),
                Astronaut(id="a2", name="Jordan"),
                Astronaut(id="a3", name="Sam"),
                Astronaut(id="a4", name="Riley"),
            ]
        if self.plants is None:
            self.plants = [
                Plant("Potato",  count=10, growth_cycle_days=90, area_m2=5.0),
                Plant("Lettuce", count=15, growth_cycle_days=35, area_m2=4.0),
                Plant("Radish",  count=20, growth_cycle_days=25, area_m2=3.0),
                Plant("Beans",   count=8,  growth_cycle_days=60, area_m2=3.0),
                Plant("Herbs",   count=5,  growth_cycle_days=30, area_m2=1.0),
            ]
        if self.resources is None:
            self.resources = Resources()
        if self.inventory is None:
            self.inventory = Inventory()

    def tick(self):
        self.day += 1
        for plant in self.plants:
            plant.hydration = max(0.0, plant.hydration - 2.0)
            plant.days_planted += 1
        per_astronaut = self.inventory.consume_for_astronauts(self.astronauts)
        water_per = self.resources.water_liters / max(1, len([a for a in self.astronauts if a.isAlive]))
        for a in self.astronauts:
            if not a.isAlive:
                continue
            water_given = min(a.dailyWaterNeedL, water_per)
            self.resources.water_liters = max(0.0, self.resources.water_liters - water_given)
            a.tick(
                kcal_consumed      = per_astronaut.get("kcal", 0.0),
                protein_consumed_g = per_astronaut.get("protein", 0.0),
                water_consumed_l   = water_given,
                vit_a              = per_astronaut.get("vit_a", 0.0),
                vit_c              = per_astronaut.get("vit_c", 0.0),
                vit_k              = per_astronaut.get("vit_k", 0.0),
                folate             = per_astronaut.get("folate", 0.0),
                potassium          = per_astronaut.get("potassium", 0.0),
            )

    def to_dict(self):
        return {
            "day": self.day,
            "astronauts": [asdict(a) for a in self.astronauts],
            "plants":     [asdict(p) for p in self.plants],
            "resources":  asdict(self.resources),
            "inventory":  asdict(self.inventory),
        }


BASE         = os.path.dirname(__file__)
STATE_FILE   = os.path.join(BASE, "state.json")
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
    state.plants     = [Plant(**p) for p in data["plants"]]
    state.resources  = Resources(**data["resources"])
    inv_data = data.get("inventory", {})
    state.inventory  = Inventory(**inv_data) if inv_data else Inventory()
    return state


def read_control() -> dict:
    if not os.path.exists(CONTROL_FILE):
        return {"paused": False, "reset": False}
    with open(CONTROL_FILE) as f:
        return json.load(f)


def write_control(paused: bool, reset: bool = False):
    with open(CONTROL_FILE, "w") as f:
        json.dump({"paused": paused, "reset": reset}, f)


def run(days: int = 450, tick_delay: float = 3.0):
    write_control(paused=False)
    state = load_state()
    print(f"Starting from day {state.day}")
    print("TIP: Increase tick_delay for slower simulation (e.g., tick_delay=10.0)")
    while state.day < days:
        ctrl = read_control()
        if ctrl.get("reset"):
            state = SimState()
            save_state(state)
            write_control(paused=False, reset=False)
            print("Reset to day 0")
            continue
        if ctrl.get("paused"):
            time.sleep(0.2)
            continue
        state.tick()
        save_state(state)
        alive = sum(1 for a in state.astronauts if a.isAlive)
        total_emergency_rations = sum(a.storedFoodCalories for a in state.astronauts if a.isAlive)
        greenhouse_food = state.inventory.total_kcal()
        total_food = total_emergency_rations + greenhouse_food
        print(f"Day {state.day} | Alive: {alive}/4 | Food: {total_food:.0f} kcal (Emergency: {total_emergency_rations:.0f}, Greenhouse: {greenhouse_food:.0f})")
        time.sleep(tick_delay)
    print("Simulation complete.")


if __name__ == "__main__":
    import sys
    # Allow custom tick delay from command line
    # Usage: python sim.py 10.0
    tick_delay = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    run(tick_delay=tick_delay)
