from dataclasses import dataclass, field
from enum import Enum

class Species(str, Enum):
    LETTUCE = "LETTUCE"
    POTATO  = "POTATO"
    RADISH  = "RADISH"
    BEAN    = "BEAN"
    HERB    = "HERB"

class GrowthStage(str, Enum):
    GERMINATION = "GERMINATION"
    SEEDLING    = "SEEDLING"
    VEGETATIVE  = "VEGETATIVE"
    FLOWERING   = "FLOWERING"
    FRUITING    = "FRUITING"
    HARVEST     = "HARVEST"

class WaterDemand(str, Enum):
    HIGH     = "HIGH"
    MODERATE = "MODERATE"
    LOW      = "LOW"

class StressType(str, Enum):
    NONE        = "NONE"
    DROUGHT     = "DROUGHT"
    HEAT        = "HEAT"
    COLD        = "COLD"
    NUTRIENT_N  = "NUTRIENT_N"
    NUTRIENT_K  = "NUTRIENT_K"
    NUTRIENT_FE = "NUTRIENT_FE"
    SALINITY    = "SALINITY"
    HYPOXIA     = "HYPOXIA"
    DISEASE     = "DISEASE"

class StressSeverity(str, Enum):
    NONE     = "NONE"
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Plant:
    # Identity
    id: str
    species: Species
    zone: str

    # Growth state
    growthStage: GrowthStage = GrowthStage.GERMINATION
    ageDays: int = 0
    growthCycleDays: int = 0        # set by species defaults
    harvestIndex: float = 0.0
    areaM2: float = 0.25
    currentBiomassKg: float = 0.0
    estimatedYieldKgM2: float = 0.0

    # Environmental requirements (optimal ranges)
    optimalTempMinC: float = 0.0
    optimalTempMaxC: float = 0.0
    heatStressThresholdC: float = 0.0
    lightRequirementPAR: float = 0.0   # µmol/m²/s
    optimalHumidityMin: float = 50.0
    optimalHumidityMax: float = 70.0
    optimalCO2Ppm: float = 1000.0
    optimalPhMin: float = 5.5
    optimalPhMax: float = 6.5
    waterDemand: WaterDemand = WaterDemand.MODERATE

    # Current stress state
    healthScore: float = 1.0
    activeStress: StressType = StressType.NONE
    stressSeverity: StressSeverity = StressSeverity.NONE
    leafWilting: bool = False
    leafDiscoloration: bool = False
    leafEdgeBurn: bool = False
    stunted: bool = False

    # Nutritional output per 100g (USDA FoodData Central)
    kcalPer100g: float = 0.0
    proteinPer100g: float = 0.0
    providesVitaminA: bool = False
    providesVitaminC: bool = False
    providesVitaminK: bool = False
    providesFolate: bool = False
    providesPotassium: bool = False


# ---------------------------------------------------------------------------
# Species defaults — values sourced from:
#   Nutrition: USDA FoodData Central (fdc.nal.usda.gov)
#   Growing conditions: NASA VEGGIE program, SAE 2005-01-2820,
#                       hydroponic space agriculture literature
# ---------------------------------------------------------------------------

SPECIES_DEFAULTS: dict[Species, dict] = {

    Species.LETTUCE: {
        # Growth — 30–45 day cycle, fast-growing leafy crop
        "growthCycleDays": 35,
        "harvestIndex": 0.85,          # ~85% of biomass is edible leaf
        "estimatedYieldKgM2": 4.0,     # 3–5 kg/m² typical hydroponic yield

        # Temperature — cool-season crop, bolts above 25 °C
        # Source: SAE 2005-01-2820; Colorado State Extension
        "optimalTempMinC": 15.0,
        "optimalTempMaxC": 22.0,
        "heatStressThresholdC": 25.0,

        # Light — low-to-moderate PAR requirement
        # Source: NASA VEGGIE program (150–250 µmol/m²/s)
        "lightRequirementPAR": 200.0,

        # Humidity & CO2
        "optimalHumidityMin": 50.0,
        "optimalHumidityMax": 70.0,
        "optimalCO2Ppm": 1000.0,

        # pH — slightly acidic, standard hydroponic range
        "optimalPhMin": 6.0,
        "optimalPhMax": 7.0,

        "waterDemand": WaterDemand.HIGH,   # shallow roots, frequent irrigation

        # Nutrition per 100g — USDA #11252 (green leaf lettuce, raw)
        "kcalPer100g": 15.0,
        "proteinPer100g": 1.4,
        "providesVitaminA": True,   # 166 µg RAE / 100g
        "providesVitaminC": True,   # 9.2 mg / 100g
        "providesVitaminK": True,   # 126 µg / 100g
        "providesFolate": True,     # 38 µg / 100g
        "providesPotassium": False,
    },

    Species.POTATO: {
        # Growth — 70–120 day cycle, tuber crop
        "growthCycleDays": 90,
        "harvestIndex": 0.75,          # tuber fraction of total biomass
        "estimatedYieldKgM2": 6.0,     # 4–8 kg/m² hydroponic/aeroponic

        # Temperature — cool-season tuber; tuber set fails above 28 °C
        # Source: FAO potato agronomy; NASA Advanced Plant Habitat data
        "optimalTempMinC": 15.0,
        "optimalTempMaxC": 25.0,
        "heatStressThresholdC": 28.0,

        # Light — higher PAR needed for canopy photosynthesis
        "lightRequirementPAR": 300.0,  # 200–400 µmol/m²/s

        "optimalHumidityMin": 60.0,
        "optimalHumidityMax": 80.0,
        "optimalCO2Ppm": 1000.0,

        "optimalPhMin": 5.0,
        "optimalPhMax": 6.0,           # slightly more acidic than lettuce

        "waterDemand": WaterDemand.HIGH,

        # Nutrition per 100g — USDA #11352 (potato, flesh & skin, raw)
        "kcalPer100g": 77.0,
        "proteinPer100g": 2.0,
        "providesVitaminA": False,
        "providesVitaminC": True,   # 19.7 mg / 100g
        "providesVitaminK": False,
        "providesFolate": True,     # 15 µg / 100g
        "providesPotassium": True,  # 421 mg / 100g — excellent source
    },

    Species.RADISH: {
        # Growth — fastest crop, 21–30 days
        "growthCycleDays": 25,
        "harvestIndex": 0.70,          # taproot fraction
        "estimatedYieldKgM2": 3.0,     # 2–4 kg/m²

        # Temperature — very cold-tolerant, bolts quickly in heat
        # Source: SAE 2005-01-2820 (Cherry Bomb II at 25–28 °C)
        "optimalTempMinC": 10.0,
        "optimalTempMaxC": 22.0,
        "heatStressThresholdC": 26.0,

        "lightRequirementPAR": 175.0,  # moderate, similar to lettuce

        "optimalHumidityMin": 50.0,
        "optimalHumidityMax": 70.0,
        "optimalCO2Ppm": 1000.0,

        "optimalPhMin": 6.0,
        "optimalPhMax": 7.0,

        "waterDemand": WaterDemand.MODERATE,

        # Nutrition per 100g — USDA #11429 (radish, raw)
        "kcalPer100g": 16.0,
        "proteinPer100g": 0.7,
        "providesVitaminA": False,
        "providesVitaminC": True,   # 14.8 mg / 100g
        "providesVitaminK": False,
        "providesFolate": True,     # 25 µg / 100g
        "providesPotassium": True,  # 233 mg / 100g
    },

    Species.BEAN: {
        # Growth — 50–70 days; includes flowering + pod fill
        "growthCycleDays": 60,
        "harvestIndex": 0.55,          # pod/seed fraction
        "estimatedYieldKgM2": 3.0,     # 2–4 kg/m² for bush bean

        # Temperature — warm-season legume; chilling injury below 10 °C
        # Source: FAO bean agronomy; hydroponic bean literature
        "optimalTempMinC": 18.0,
        "optimalTempMaxC": 28.0,
        "heatStressThresholdC": 30.0,

        "lightRequirementPAR": 350.0,  # high light for pod fill

        "optimalHumidityMin": 50.0,
        "optimalHumidityMax": 70.0,
        "optimalCO2Ppm": 1000.0,

        "optimalPhMin": 6.0,
        "optimalPhMax": 7.0,

        "waterDemand": WaterDemand.MODERATE,

        # Nutrition per 100g — USDA #16057 (navy bean, cooked) /
        #                       #11052 (snap bean, raw) blended for dry bean
        # Using dry/mature bean values as primary caloric source
        "kcalPer100g": 100.0,          # 80–120 kcal depending on variety
        "proteinPer100g": 7.0,         # 5–9g; excellent plant protein
        "providesVitaminA": False,
        "providesVitaminC": True,   # snap bean: 12.2 mg / 100g
        "providesVitaminK": False,
        "providesFolate": True,     # 130 µg / 100g — very high
        "providesPotassium": True,  # 405 mg / 100g
    },

    Species.HERB: {
        # Growth — continuous harvest, ~30 day establishment
        "growthCycleDays": 30,
        "harvestIndex": 0.80,
        "estimatedYieldKgM2": 1.5,     # lower yield, high value micronutrients

        # Basil/parsley/chives blend — moderate temp range
        "optimalTempMinC": 18.0,
        "optimalTempMaxC": 26.0,
        "heatStressThresholdC": 30.0,

        "lightRequirementPAR": 200.0,

        "optimalHumidityMin": 50.0,
        "optimalHumidityMax": 70.0,
        "optimalCO2Ppm": 1000.0,

        "optimalPhMin": 5.5,
        "optimalPhMax": 6.5,

        "waterDemand": WaterDemand.MODERATE,

        # Nutrition per 100g — USDA #02044 (basil, fresh)
        "kcalPer100g": 23.0,
        "proteinPer100g": 3.2,
        "providesVitaminA": True,   # 264 µg RAE / 100g
        "providesVitaminC": True,   # 18 mg / 100g
        "providesVitaminK": True,   # 415 µg / 100g — extremely high
        "providesFolate": True,     # 68 µg / 100g
        "providesPotassium": True,  # 295 mg / 100g
    },
}


def create_plant(id: str, species: Species, zone: str, area_m2: float = 0.25) -> Plant:
    """Instantiate a Plant with species-accurate defaults."""
    defaults = SPECIES_DEFAULTS[species]
    return Plant(
        id=id,
        species=species,
        zone=zone,
        areaM2=area_m2,
        **defaults,
    )
