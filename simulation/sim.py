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
    """Martian conditions including dust storm support."""
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

    # Dust storm state
    dust_storm_active: bool = False
    dust_storm_days_remaining: int = 0
    dust_storm_severity: float = 0.0            # 0 = none, 0.6 = medium

    # Water recycling failure state
    water_failure_active: bool = False
    water_failure_days_remaining: int = 0

    # Meteorite strike state
    meteorite_struck: bool = False               # One-shot flag, cleared after processing
    meteorite_area_lost: float = 0.0             # m² destroyed this strike

    # Solar flare state
    solar_flare_active: bool = False
    solar_flare_days_remaining: int = 0

    # Meteorite repair state
    repair_active: bool = False
    repair_days_remaining: int = 0
    repair_astronaut_id: str = ""               # ID of astronaut doing EVA repair
    repair_area_target: float = 450.0           # Growing area to restore to
    repair_destroyed_plants: str = ""           # JSON list of destroyed plant specs for replanting

    def effective_par(self) -> float:
        """Total PAR inside greenhouse. Storm blocks sunlight, LEDs partially compensate."""
        solar_par = 250.0 * (self.solar_irradiance_wm2 / 590.0)
        if self.dust_storm_active:
            # Storm blocks most sunlight; LEDs run at reduced capacity (less power available)
            solar_par *= (1.0 - self.dust_storm_severity)
            led_par = self.led_supplement_par * (1.0 - self.dust_storm_severity * 0.4)
        else:
            led_par = self.led_supplement_par
        return max(50.0, min(500.0, solar_par + led_par))

    def effective_radiation(self) -> float:
        """Radiation dose reaching inside greenhouse (mSv/day). Solar flare = 5× spike."""
        base = self.radiation_msv_per_day * (1.0 - self.greenhouse_shielding)
        if self.solar_flare_active:
            base *= 5.0  # Flare overwhelms shielding
        return base

    def effective_greenhouse_temp(self) -> float:
        """Greenhouse temp drops during storms (less solar heating, more energy to heating)."""
        if self.dust_storm_active:
            # Temp drops 5-15°C depending on severity — heating can't fully compensate
            return self.greenhouse_temp_c - self.dust_storm_severity * 20.0
        return self.greenhouse_temp_c

    def water_recycling_efficiency(self) -> float:
        """Normally 90%. Storm or pump failure reduces it."""
        eff = 0.90
        if self.dust_storm_active:
            eff -= self.dust_storm_severity * 0.25
        if self.water_failure_active:
            eff = min(eff, 0.45)  # Pump failure caps at 45%
        return max(0.10, eff)


    def growth_modifier(self) -> float:
        """Combined modifier on plant growth from Mars conditions + storm effects."""
        # Gravity effect: 0.85 + gravity_factor * 0.15 → 0.907 on Mars
        grav_mod = 0.85 + self.gravity_factor * 0.15
        # CO2 effect
        if self.greenhouse_co2_ppm < 400:
            co2_mod = 0.70
        elif self.greenhouse_co2_ppm <= 1200:
            co2_mod = 1.0
        else:
            co2_mod = 0.95
        # PAR effect: below 200 µmol/m²/s plants grow slower
        par = self.effective_par()
        if par < 200:
            light_mod = 0.5 + (par / 200.0) * 0.5  # Linear from 0.5 to 1.0
        else:
            light_mod = 1.0
        # Cold stress during storm
        temp = self.effective_greenhouse_temp()
        if temp < 15.0:
            temp_mod = 0.6 + (temp / 15.0) * 0.4  # Linear from 0.6 to 1.0
        else:
            temp_mod = 1.0
        return grav_mod * co2_mod * light_mod * temp_mod

    def trigger_dust_storm(self, severity: float = 0.6, duration_days: int = 12):
        """Activate a dust storm. Severity 0.6 = medium-strong."""
        self.dust_storm_active = True
        self.dust_storm_severity = max(0.1, min(1.0, severity))
        self.dust_storm_days_remaining = duration_days

    def trigger_water_failure(self, duration_days: int = 10):
        """Pump failure — recycling drops to 45% for duration."""
        self.water_failure_active = True
        self.water_failure_days_remaining = duration_days

    def trigger_meteorite(self, area_lost_m2: float = 50.0):
        """One-shot meteorite strike. Destroys growing area + kills plants."""
        self.meteorite_struck = True
        self.meteorite_area_lost = area_lost_m2

    def trigger_solar_flare(self, duration_days: int = 3):
        """Radiation spike — 5× normal for a few days."""
        self.solar_flare_active = True
        self.solar_flare_days_remaining = duration_days

    def tick_storm(self):
        """Advance storm by one day. Auto-resolves when days run out."""
        if not self.dust_storm_active:
            return
        self.dust_storm_days_remaining -= 1
        if self.dust_storm_days_remaining <= 0:
            self.dust_storm_active = False
            self.dust_storm_severity = 0.0
            self.dust_storm_days_remaining = 0

    def tick_events(self, resources=None, sim_state=None):
        """Advance all non-storm event timers."""
        if self.water_failure_active:
            self.water_failure_days_remaining -= 1
            if self.water_failure_days_remaining <= 0:
                self.water_failure_active = False
                self.water_failure_days_remaining = 0
        if self.solar_flare_active:
            self.solar_flare_days_remaining -= 1
            if self.solar_flare_days_remaining <= 0:
                self.solar_flare_active = False
                self.solar_flare_days_remaining = 0
        # Repair: restore 5 m²/day
        if self.repair_active and resources is not None:
            resources.growing_area_m2 = min(self.repair_area_target, resources.growing_area_m2 + 5.0)
            self.repair_days_remaining -= 1
            if self.repair_days_remaining <= 0 or resources.growing_area_m2 >= self.repair_area_target:
                # Replant destroyed crops
                if sim_state is not None and self.repair_destroyed_plants:
                    import json as _json
                    try:
                        specs = _json.loads(self.repair_destroyed_plants)
                        for spec in specs:
                            new_plant = Plant(
                                name=spec["name"],
                                area_m2=spec["area_m2"],
                                growth_cycle_days=spec["growth_cycle_days"],
                                hydration=100.0,
                                days_planted=0
                            )
                            sim_state.plants.append(new_plant)
                    except:
                        pass
                self.repair_active = False
                self.repair_days_remaining = 0
                self.repair_astronaut_id = ""
                self.repair_destroyed_plants = ""
        # Meteorite is one-shot, cleared after processing in tick()
        self.meteorite_struck = False
        self.meteorite_area_lost = 0.0


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
            # Eat whatever emergency rations are available (even partial)
            eaten = min(a.storedFoodCalories, share)
            if eaten > 0:
                a.storedFoodCalories -= eaten
                nutrients["kcal"] += eaten
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
                Astronaut(id="a1", name="Amelie"),
                Astronaut(id="a2", name="Jessica"),
                Astronaut(id="a3", name="Amadine"),
                Astronaut(id="a4", name="Max"),
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

        # ── Mars growth modifier (gravity + CO₂ + light + temp) ──────────
        growth_mod = self.mars_env.growth_modifier()
        effective_rad = self.mars_env.effective_radiation()
        is_storm = self.mars_env.dust_storm_active

        for plant in self.plants:
            # Hydration drain — faster in low-g, worse during storms (cold stress)
            base_drain = 2.0 / growth_mod
            if is_storm:
                # Cold + dry air during storm increases water loss
                base_drain += self.mars_env.dust_storm_severity * 1.5
            plant.hydration = max(0.0, plant.hydration - base_drain)
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
                # Mars conditions + storm reduce yield
                kg = plant.harvest_kg() * growth_mod
                current = getattr(self.inventory, plant.name, 0.0)
                setattr(self.inventory, plant.name, round(current + kg, 3))
                plant.days_planted = 0
                plant.hydration = 100.0
        
        per_astronaut = self.inventory.consume_for_astronauts(self.astronauts)
        alive_list = [a for a in self.astronauts if a.isAlive]
        water_per = self.resources.water_liters / max(1, len(alive_list))
        recycling_eff = self.mars_env.water_recycling_efficiency()

        for a in self.astronauts:
            if not a.isAlive:
                continue
            water_given = min(a.dailyWaterNeedL, water_per)
            self.resources.water_liters = max(0.0, self.resources.water_liters - water_given)
            # Water recycling: efficiency depends on storm state
            self.resources.water_liters += water_given * recycling_eff
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
            gravity_bone_penalty = (2.0 - self.mars_env.gravity_factor)
            a.boneHealthScore = max(0.0, a.boneHealthScore - 0.0003 * gravity_bone_penalty)
            # ── Mars radiation: slow immune degradation ──────────────────
            a.immuneScore = max(0.0, a.immuneScore - effective_rad * 0.0005)
            # ── High CO₂ cognitive effect (>1500 ppm) ────────────────────
            if self.mars_env.greenhouse_co2_ppm > 1500:
                a.cognitivePerformance = max(0.0, a.cognitivePerformance - 0.001)

        # ── Meteorite strike: destroy plants + reduce growing area ─────────
        if self.mars_env.meteorite_struck:
            area_to_destroy = self.mars_env.meteorite_area_lost
            # Remember target for repair
            area_before = self.resources.growing_area_m2
            self.resources.growing_area_m2 = max(50.0, self.resources.growing_area_m2 - area_to_destroy)
            # Kill plants in the destroyed area (remove from end)
            destroyed_area = 0.0
            destroyed_plants = []
            for p in reversed(self.plants):
                if destroyed_area >= area_to_destroy:
                    break
                destroyed_area += p.area_m2
                destroyed_plants.append(p)
            for p in destroyed_plants:
                self.plants.remove(p)
            # Auto-assign healthiest astronaut to repair duty
            repair_candidates = [a for a in self.astronauts if a.isAlive]
            if repair_candidates:
                best = max(repair_candidates, key=lambda a: a.micronutrientScore + a.hydrationLevel)
                repair_days = max(1, int(area_to_destroy / 5.0))  # 5 m²/day
                self.mars_env.repair_active = True
                self.mars_env.repair_days_remaining = repair_days
                self.mars_env.repair_astronaut_id = best.id
                self.mars_env.repair_area_target = area_before
                # Save destroyed plants for replanting after repair
                import json as _json
                destroyed_specs = [{"name": p.name, "area_m2": p.area_m2, "growth_cycle_days": p.growth_cycle_days} for p in destroyed_plants]
                self.mars_env.repair_destroyed_plants = _json.dumps(destroyed_specs)

        # ── Repair penalties: repairing astronaut works harder ───────────
        if self.mars_env.repair_active:
            for a in self.astronauts:
                if a.id == self.mars_env.repair_astronaut_id and a.isAlive:
                    # EVA repair = 50% more calorie burn (adds 1500 kcal deficit)
                    a.calorieDeficitAccumulated += 1500.0
                    # Physical strain: hydration and bone penalties
                    a.hydrationLevel = max(0.0, a.hydrationLevel - 0.02)
                    a.boneHealthScore = max(0.0, a.boneHealthScore - 0.001)
                    break

        # ── Solar flare: extra radiation damage to astronauts ────────────
        if self.mars_env.solar_flare_active:
            for a in self.astronauts:
                if not a.isAlive:
                    continue
                # Flare hammers immune system and hydration
                a.immuneScore = max(0.0, a.immuneScore - 0.008)
                a.hydrationLevel = max(0.0, a.hydrationLevel - 0.005)

        # ── Advance event timers (at end so effects apply on last day) ───
        self.mars_env.tick_storm()
        self.mars_env.tick_events(resources=self.resources, sim_state=self)
    
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
    try:
        with open(STATE_FILE) as f:
            content = f.read()
        if not content.strip():
            return SimState()
        data = json.loads(content)
    except (json.JSONDecodeError, IOError):
        return SimState()
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


def write_control(paused: bool, reset: bool = False, trigger_storm: bool = False,
                  trigger_water_failure: bool = False, trigger_meteorite: bool = False,
                  trigger_solar_flare: bool = False):
    with open(CONTROL_FILE, "w") as f:
        json.dump({
            "paused": paused, "reset": reset,
            "trigger_storm": trigger_storm,
            "trigger_water_failure": trigger_water_failure,
            "trigger_meteorite": trigger_meteorite,
            "trigger_solar_flare": trigger_solar_flare,
        }, f)


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
        # Check for all event triggers from frontend (read once, clear once)
        t_storm = ctrl.get("trigger_storm") and not state.mars_env.dust_storm_active
        t_water = ctrl.get("trigger_water_failure") and not state.mars_env.water_failure_active
        t_meteor = ctrl.get("trigger_meteorite")
        t_flare = ctrl.get("trigger_solar_flare") and not state.mars_env.solar_flare_active

        if t_storm or t_water or t_meteor or t_flare:
            # Clear all triggers in one write to avoid race conditions
            write_control(paused=False)

        if t_storm:
            state.mars_env.trigger_dust_storm(severity=0.6, duration_days=12)
            print(f"🌪️ DUST STORM TRIGGERED! Severity: 60%, Duration: 12 days")
        if t_water:
            state.mars_env.trigger_water_failure(duration_days=10)
            print(f"💧 WATER RECYCLING FAILURE! Recycling drops to 45% for 10 days")
        if t_meteor:
            state.mars_env.trigger_meteorite(area_lost_m2=50.0)
            print(f"☄️ METEORITE STRIKE! ~50 m² of growing area destroyed")
        if t_flare:
            state.mars_env.trigger_solar_flare(duration_days=3)
            print(f"☀️ SOLAR FLARE! Radiation 5× for 3 days")
        state.tick()
        save_state(state)
        alive = sum(1 for a in state.astronauts if a.isAlive)
        total_emergency_rations = sum(a.storedFoodCalories for a in state.astronauts if a.isAlive)
        greenhouse_food = state.inventory.total_kcal()
        total_food = total_emergency_rations + greenhouse_food
        storm_tag = f" | 🌪️ STORM ({state.mars_env.dust_storm_days_remaining}d)" if state.mars_env.dust_storm_active else ""
        water_tag = f" | 💧 PUMP FAIL ({state.mars_env.water_failure_days_remaining}d)" if state.mars_env.water_failure_active else ""
        flare_tag = f" | ☀️ FLARE ({state.mars_env.solar_flare_days_remaining}d)" if state.mars_env.solar_flare_active else ""
        meteor_tag = " | ☄️ METEORITE HIT" if state.mars_env.meteorite_struck else ""
        print(f"Day {state.day} | Alive: {alive}/4 | Food: {total_food:.0f} kcal (Emergency: {total_emergency_rations:.0f}, Greenhouse: {greenhouse_food:.0f}) | Water: {state.resources.water_liters:.0f} L{storm_tag}{water_tag}{flare_tag}{meteor_tag}")
        time.sleep(tick_delay)
    print("Simulation complete.")


if __name__ == "__main__":
    import sys
    # Allow custom tick delay from command line
    # Usage: python sim.py 10.0
    tick_delay = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    run(tick_delay=tick_delay)
