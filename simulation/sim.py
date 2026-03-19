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
class MarsEnvironment:
    """Static Martian conditions — no events, just the baseline reality."""
    # Atmosphere
    external_pressure_mbar: float = 6.5         # Mars surface: 6-7 mbar
    greenhouse_pressure_mbar: float = 1013.0    # Earth-like pressurized interior
    external_co2_pct: float = 95.32             # Mars atmosphere composition
    greenhouse_co2_ppm: float = 1000.0          # Optimal for crops (800-1200)

    # Temperature
    external_temp_c: float = -63.0              # Mars average surface temp
    greenhouse_temp_c: float = 22.0             # Maintained for crops

    # Solar & Lighting
    solar_irradiance_wm2: float = 590.0         # ~43% of Earth (1361 W/m²)
    led_supplement_par: float = 200.0           # LED PAR µmol/m²/s

    # Radiation (no magnetic field, thin atmosphere)
    radiation_msv_per_day: float = 0.67         # Surface dose rate
    greenhouse_shielding: float = 0.70          # 70% blocked by structure

    # Gravity
    gravity_ms2: float = 3.721                  # 38% of Earth (9.81 m/s²)
    gravity_factor: float = 0.38

    def effective_par(self) -> float:
        """Total PAR available inside greenhouse (µmol/m²/s)."""
        # Mars solar contributes ~250 µmol/m²/s at equator noon (43% of Earth)
        solar_par = 250.0 * (self.solar_irradiance_wm2 / 590.0)
        return min(500.0, solar_par + self.led_supplement_par)

    def effective_radiation(self) -> float:
        """Radiation dose reaching inside greenhouse (mSv/day)."""
        return self.radiation_msv_per_day * (1.0 - self.greenhouse_shielding)

    def growth_modifier(self) -> float:
        """Combined modifier on plant growth from Mars conditions.
        Gravity: ~91% efficiency (plants grow slightly slower in 0.38g).
        CO2: optimal at 800-1200 ppm (bonus), reduced below 400 ppm.
        """
        # Gravity effect: 0.85 + gravity_factor * 0.15 → 0.907 on Mars
        grav_mod = 0.85 + self.gravity_factor * 0.15
        # CO2 effect
        if self.greenhouse_co2_ppm < 400:
            co2_mod = 0.70
        elif self.greenhouse_co2_ppm <= 1200:
            co2_mod = 1.0  # Optimal range
        else:
            co2_mod = 0.95  # Slightly too high
        return grav_mod * co2_mod


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
        # Recovery rate scales with deficit severity: eat more when in danger
        if self.calorieDeficitAccumulated > 60000.0:
            recovery_rate = 1.0  # Critical: full surplus recovers deficit
        elif self.calorieDeficitAccumulated > 30000.0:
            recovery_rate = 0.8  # High: 80% recovery
        else:
            recovery_rate = 0.5  # Normal: 50% recovery
        self.calorieDeficitAccumulated = max(0.0, self.calorieDeficitAccumulated + cal_deficit - cal_surplus * recovery_rate)
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
    area_m2: float  # Area allocated to this plant instance
    hydration: float = 100.0
    days_planted: int = 0
    growth_cycle_days: int = 30
    plant_id: str = ""  # Unique identifier

    def __post_init__(self):
        if not self.plant_id:
            import uuid
            self.plant_id = str(uuid.uuid4())[:8]

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
    
    def water_needed_per_day(self) -> float:
        """Calculate daily water need based on area."""
        # Base: 0.5L per m² per day
        return self.area_m2 * 0.5


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
    water_liters: float    = 30000.0
    growing_area_m2: float = 450.0  # Increased from 150m² to support 4 astronauts
    energy_kwh: float      = 500.0
    
    def available_growing_area(self, plants: list) -> float:
        """Calculate remaining unplanted area."""
        used_area = sum(p.area_m2 for p in plants)
        return max(0.0, self.growing_area_m2 - used_area)


@dataclass
class SimState:
    day: int = 0
    astronauts: list = None
    plants: list = None  # Now a dynamic list that starts empty
    resources: Resources = None
    inventory: Inventory = None
    mars_env: MarsEnvironment = None

    def __post_init__(self):
        if self.astronauts is None:
            self.astronauts = [
                Astronaut(id="a1", name="Alex"),
                Astronaut(id="a2", name="Jordan"),
                Astronaut(id="a3", name="Sam"),
                Astronaut(id="a4", name="Riley"),
            ]
        if self.plants is None:
            self.plants = []
        if self.resources is None:
            self.resources = Resources()
        if self.inventory is None:
            self.inventory = Inventory()
        if self.mars_env is None:
            self.mars_env = MarsEnvironment()

    def tick(self):
        self.day += 1

        # ── Mars growth modifier (gravity + CO₂) ────────────────────────
        growth_mod = self.mars_env.growth_modifier()  # ~0.907 nominal
        effective_rad = self.mars_env.effective_radiation()  # mSv/day inside

        for plant in self.plants:
            # Hydration drain slightly faster in low-g (altered transpiration)
            plant.hydration = max(0.0, plant.hydration - 2.0 / growth_mod)
            # Radiation stress: minor hydration penalty
            plant.hydration = max(0.0, plant.hydration - effective_rad * 0.3)
            plant.days_planted += 1

        # Auto-water plants that drop below 60% hydration
        for plant in self.plants:
            if plant.hydration < 60.0:
                water_needed = plant.water_needed_per_day()
                if self.resources.water_liters >= water_needed:
                    self.resources.water_liters -= water_needed
                    plant.hydration = min(100.0, plant.hydration + 8.0)
        
        # Auto-harvest mature plants directly into inventory
        for plant in self.plants:
            if plant.is_harvestable():
                # Mars conditions reduce yield slightly via growth_mod
                kg = plant.harvest_kg() * growth_mod
                current = getattr(self.inventory, plant.name, 0.0)
                setattr(self.inventory, plant.name, round(current + kg, 3))
                plant.days_planted = 0
                plant.hydration = 100.0
        
        per_astronaut = self.inventory.consume_for_astronauts(self.astronauts)
        water_per = self.resources.water_liters / max(1, len([a for a in self.astronauts if a.isAlive]))
        for a in self.astronauts:
            if not a.isAlive:
                continue
            water_given = min(a.dailyWaterNeedL, water_per)
            self.resources.water_liters = max(0.0, self.resources.water_liters - water_given)
            # Water recycling: 90% recovery via transpiration capture
            self.resources.water_liters += water_given * 0.90
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
            # ── Mars gravity: accelerated bone loss (1.62× Earth rate) ───
            gravity_bone_penalty = (2.0 - self.mars_env.gravity_factor)  # ~1.62
            a.boneHealthScore = max(0.0, a.boneHealthScore - 0.0003 * gravity_bone_penalty)
            # ── Mars radiation: slow immune degradation ──────────────────
            a.immuneScore = max(0.0, a.immuneScore - effective_rad * 0.0005)
            # ── High CO₂ cognitive effect (>1500 ppm) ────────────────────
            if self.mars_env.greenhouse_co2_ppm > 1500:
                a.cognitivePerformance = max(0.0, a.cognitivePerformance - 0.001)
    
    def plant_crop(self, crop_name: str, area_m2: float) -> dict:
        """Plant a new crop. Returns success status."""
        available = self.resources.available_growing_area(self.plants)
        if area_m2 > available:
            return {"success": False, "message": f"Not enough space. Available: {available:.1f}m²"}
        
        # Get growth cycle for this crop
        growth_cycles = {"Potato": 90, "Lettuce": 35, "Radish": 25, "Beans": 60, "Herbs": 30}
        growth_cycle = growth_cycles.get(crop_name, 30)
        
        new_plant = Plant(
            name=crop_name,
            area_m2=area_m2,
            growth_cycle_days=growth_cycle,
            hydration=100.0,
            days_planted=0
        )
        self.plants.append(new_plant)
        return {"success": True, "message": f"Planted {area_m2:.1f}m² of {crop_name}", "plant_id": new_plant.plant_id}
    
    def remove_plant(self, plant_id: str) -> dict:
        """Remove/kill a plant to free up space."""
        for i, plant in enumerate(self.plants):
            if plant.plant_id == plant_id:
                removed = self.plants.pop(i)
                return {"success": True, "message": f"Removed {removed.name} ({removed.area_m2:.1f}m²)", "freed_area": removed.area_m2}
        return {"success": False, "message": "Plant not found"}

    def to_dict(self):
        return {
            "day": self.day,
            "astronauts": [asdict(a) for a in self.astronauts],
            "plants":     [asdict(p) for p in self.plants],
            "resources":  asdict(self.resources),
            "inventory":  asdict(self.inventory),
            "mars_env":   asdict(self.mars_env),
        }


BASE         = os.path.dirname(__file__)
STATE_FILE   = os.path.join(BASE, "state.json")
CONTROL_FILE = os.path.join(BASE, "control.json")


def save_state(state: SimState):
    # Debug: Log plant count when saving
    plant_count = len(state.plants)
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_dict(), f)
    # Verify the save
    if plant_count > 0:
        with open(STATE_FILE, "r") as f:
            saved_data = json.load(f)
            saved_plant_count = len(saved_data.get("plants", []))
            if saved_plant_count != plant_count:
                print(f"WARNING: Plant count mismatch! Expected {plant_count}, saved {saved_plant_count}")


def load_state() -> SimState:
    if not os.path.exists(STATE_FILE):
        return SimState()
    with open(STATE_FILE) as f:
        data = json.load(f)
    state = SimState(day=data["day"])
    state.astronauts = [Astronaut(**a) for a in data["astronauts"]]
    # Load plants - handle both old and new format
    state.plants = []
    for p_data in data.get("plants", []):
        # Ensure plant_id exists
        if 'plant_id' not in p_data:
            import uuid
            p_data['plant_id'] = str(uuid.uuid4())[:8]
        state.plants.append(Plant(**p_data))
    state.resources  = Resources(**data["resources"])
    inv_data = data.get("inventory", {})
    state.inventory  = Inventory(**inv_data) if inv_data else Inventory()
    env_data = data.get("mars_env", {})
    # Filter out any keys that no longer exist in MarsEnvironment
    valid_env_fields = {f.name for f in MarsEnvironment.__dataclass_fields__.values()}
    env_data = {k: v for k, v in env_data.items() if k in valid_env_fields}
    state.mars_env = MarsEnvironment(**env_data) if env_data else MarsEnvironment()
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
    
    # INITIAL PLANTING: If starting fresh (day 0) and no plants, do initial planting
    if state.day == 0 and len(state.plants) == 0:
        print("=== INITIAL GREENHOUSE SETUP ===")
        print("Planting initial crops (optimized for 12,000 kcal/day production)...")
        print("Target: 4 astronauts × 3,000 kcal/day = 12,000 kcal/day")
        initial_crops = [
            ("Potato", 300.0),  # Primary calorie source: ~10,400 kcal/day
            ("Beans", 60.0),    # Protein + calories: ~1,650 kcal/day
            ("Lettuce", 40.0),  # Micronutrients: ~582 kcal/day
            ("Radish", 30.0),   # Fast harvest: ~403 kcal/day
            ("Herbs", 20.0),    # Micronutrients: ~184 kcal/day
        ]
        total_area = sum(area for _, area in initial_crops)
        print(f"Total planting area: {total_area}m² of {state.resources.growing_area_m2}m² available")
        
        for crop_name, area in initial_crops:
            result = state.plant_crop(crop_name, area)
            if result["success"]:
                print(f"  ✓ {result['message']}")
            else:
                print(f"  ✗ {result['message']}")
        save_state(state)
        print(f"=== Initial planting complete: {len(state.plants)} plants ===")
        print(f"Expected daily production: ~13,219 kcal/day (target: 12,000 kcal/day)")
        print()
    
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
        print(f"Day {state.day} | Alive: {alive}/4 | Food: {total_food:.0f} kcal (Emergency: {total_emergency_rations:.0f}, Greenhouse: {greenhouse_food:.0f}) | Water: {state.resources.water_liters:.0f} L")
        time.sleep(tick_delay)
    print("Simulation complete.")


if __name__ == "__main__":
    import sys
    # Allow custom tick delay from command line
    # Usage: python sim.py 10.0
    tick_delay = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    run(tick_delay=tick_delay)
