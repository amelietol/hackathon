import time
import base64
import streamlit as st
from sim import (load_state, save_state, read_control, write_control,
                 SPECIES_KCAL_PER_100G, DAILY_CALORIE_NEED)

st.set_page_config(page_title="Mars Base Simulation", layout="wide")

# Set background image
def set_background(image_path):
    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
        b64_encoded = base64.b64encode(img_data).decode()
        
        st.markdown(f"""
        <style>
            .stApp {{
                background-image: url("data:image/png;base64,{b64_encoded}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                image-rendering: pixelated;
                image-rendering: -moz-crisp-edges;
                image-rendering: crisp-edges;
            }}
            /* Make text dark red */
            h1, h2, h3, p, label, .stMarkdown, span, div {{
                color: #8B0000 !important;
            }}
            /* Hide Streamlit header and menu */
            header {{
                visibility: hidden;
            }}
            #MainMenu {{
                visibility: hidden;
            }}
            footer {{
                visibility: hidden;
            }}
        </style>
        """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Background image not found. Using default background.")

set_background("hintergrund _final.png")

st.title("🚀 Mars Base — Day Survival Simulation")

ctrl      = read_control()
is_paused = ctrl.get("paused", False)

c1, c2, c3, _ = st.columns([1, 1, 1.5, 4.5])
with c1:
    if is_paused:
        if st.button("▶️ Resume"):
            write_control(paused=False); st.rerun()
    else:
        if st.button("⏸️ Pause"):
            write_control(paused=True); st.rerun()
with c2:
    if st.button("🔄 Restart"):
        write_control(paused=False, reset=True); st.rerun()
with c3:
    state_peek = load_state()
    storm_active = state_peek.mars_env.dust_storm_active if hasattr(state_peek, 'mars_env') and state_peek.mars_env else False
    if storm_active:
        st.button("🌪️ Storm Active", disabled=True)
    else:
        if st.button("🌪️ Dust Storm"):
            write_control(paused=False, trigger_storm=True); st.rerun()

st.caption(f"{'⏸ Paused' if is_paused else '▶ Running'}")

state = load_state()
st.subheader(f"📅 Day {state.day} / 450")

# Dust storm warning banner
if hasattr(state, 'mars_env') and state.mars_env and state.mars_env.dust_storm_active:
    env = state.mars_env
    temp_now = env.effective_greenhouse_temp()
    temp_drop = env.greenhouse_temp_c - temp_now
    st.error(
        f"🌪️ DUST STORM IN PROGRESS — {env.dust_storm_days_remaining} days remaining\n\n"
        f"Severity: {env.dust_storm_severity*100:.0f}% · "
        f"Greenhouse temp dropped from {env.greenhouse_temp_c:.0f}°C → {temp_now:.0f}°C (−{temp_drop:.0f}°C) · "
        f"Light: {env.effective_par():.0f} µmol/m²/s (normal: 450) · "
        f"Water recycling: {env.water_recycling_efficiency()*100:.0f}% (normal: 90%) · "
        f"Growth rate: {env.growth_modifier()*100:.0f}% (normal: 91%)"
    )

st.markdown("### 👨‍🚀 Astronauts")
cols = st.columns(4)
for idx, (col, a) in enumerate(zip(cols, state.astronauts)):
    with col:
        status = "💀 DEAD" if not a.isAlive else "✅ Alive"
        st.markdown(f"**{a.name}** — {status}")
        if not a.isAlive:
            st.error("Deceased")
            continue

        # Main health indicator - Micronutrients only
        st.markdown("🔬 Overall Health")
        st.progress(min(1.0, max(0.0, a.micronutrientScore)))
        st.caption(f"{a.micronutrientScore*100:.1f}%")
        
        # Expandable section for detailed health metrics
        with st.expander("📊 View Details"):
            def detail_bar(label, value, max_val=1.0):
                st.markdown(f"**{label}**")
                st.progress(min(1.0, max(0.0, value / max_val)))
                st.caption(f"{value/max_val*100:.1f}%")
            
            detail_bar("🫀 Hydration", a.hydrationLevel)
            detail_bar("🧠 Cognitive", a.cognitivePerformance)
            detail_bar("🦴 Bone Health", a.boneHealthScore)
            detail_bar("🛡 Immune", a.immuneScore)
            detail_bar("🔬 Micronutrients", a.micronutrientScore)

        if a.calorieDeficitAccumulated > 0:
            days_equiv = a.calorieDeficitAccumulated / a.dailyCalorieNeed
            st.caption(f"⚠️ Calorie deficit: {days_equiv:.1f} day-equiv")
        if a.proteinDeficitAccumulated > 50:
            st.caption(f"⚠️ Protein deficit: {a.proteinDeficitAccumulated:.0f}g")

        st.caption(f"🥫 Emergency food: {a.storedFoodCalories/a.dailyCalorieNeed:.1f} days left")

st.markdown("---")

st.markdown("### 📦 Food Inventory")
inv        = state.inventory
total_kcal = inv.total_kcal()
total_kg   = inv.total_kg()
alive_count = max(1, sum(1 for a in state.astronauts if a.isAlive))
days_left  = total_kcal / (DAILY_CALORIE_NEED * alive_count) if total_kcal > 0 else 0

icols = st.columns(6)
for col, name in zip(icols, ["Potato","Lettuce","Radish","Beans","Herbs"]):
    with col:
        kg   = getattr(inv, name, 0.0)
        kcal = kg * 10.0 * SPECIES_KCAL_PER_100G[name]
        st.metric(name, f"{kg:.2f} kg", f"{kcal:.0f} kcal")
with icols[5]:
    st.metric("Total", f"{total_kg:.2f} kg", f"{total_kcal:.0f} kcal")

st.caption(f"🍽 Greenhouse food covers **{days_left:.1f}** days for {alive_count} astronauts")

st.markdown("---")

st.markdown("### 🌱 Greenhouse")
stage_icon = {"seedling":"🔴","vegetative":"🟡","mature":"🟢","wilting":"🟤"}

if len(state.plants) == 0:
    st.caption("No crops planted yet.")
else:
    plant_cols = st.columns(len(state.plants))
    for idx, (col, plant) in enumerate(zip(plant_cols, state.plants)):
        with col:
            stage = plant.get_growth_stage()
            st.markdown(f"**{plant.name}** {stage_icon.get(stage,'⚪')}")
            st.caption(f"Day {plant.days_planted}/{plant.growth_cycle_days} · {stage.capitalize()}")
            st.caption(f"{plant.area_m2} m²")
            st.markdown("Hydration")
            st.progress(plant.hydration / 100.0)
            st.caption(f"{plant.hydration:.1f}%")

            if plant.is_harvestable():
                kg = plant.harvest_kg()
                if st.button(f"🌾 Harvest (~{kg:.1f} kg)", key=f"harvest_{idx}"):
                    current = getattr(state.inventory, plant.name, 0.0)
                    setattr(state.inventory, plant.name, round(current + kg, 3))
                    plant.days_planted = 0
                    save_state(state)
                    st.rerun()

st.markdown("---")

st.markdown("### ⚙️ Resources")
rcols = st.columns(3)
with rcols[0]: st.metric("Water",        f"{state.resources.water_liters:.1f} L")
with rcols[1]: st.metric("Growing Area", f"{state.resources.growing_area_m2:.1f} m²")
with rcols[2]: st.metric("Energy",       f"{state.resources.energy_kwh:.1f} kWh")

st.markdown("---")

st.markdown("### 🔴 Mars Environment")
env = state.mars_env
actual_temp = env.effective_greenhouse_temp()
actual_par = env.effective_par()

mc1, mc2, mc3, mc4 = st.columns(4)
with mc1: st.metric("🌡 External Temp",    f"{env.external_temp_c}°C")
with mc2:
    temp_delta = actual_temp - env.greenhouse_temp_c
    st.metric("🏠 Greenhouse Temp",  f"{actual_temp:.0f}°C",
              delta=f"{temp_delta:+.0f}°C" if temp_delta != 0 else "nominal")
with mc3: st.metric("☀️ Solar Irradiance",  f"{env.solar_irradiance_wm2:.0f} W/m²",
                     delta=f"{(env.solar_irradiance_wm2/1361*100):.0f}% of Earth")
with mc4:
    par_status = "⚠️ reduced" if actual_par < 400 else "nominal"
    st.metric("💡 Effective PAR",     f"{actual_par:.0f} µmol/m²/s",
              delta=par_status)

mc5, mc6, mc7, mc8 = st.columns(4)
with mc5: st.metric("🪨 Gravity",          f"{env.gravity_factor*100:.0f}% Earth",
                     delta=f"{env.gravity_ms2:.2f} m/s²")
with mc6: st.metric("☢️ Radiation (inside)", f"{env.effective_radiation():.2f} mSv/day")
with mc7: st.metric("🫁 CO₂ (greenhouse)",  f"{env.greenhouse_co2_ppm:.0f} ppm")
with mc8:
    recycling = env.water_recycling_efficiency()
    st.metric("♻️ Water Recycling",   f"{recycling*100:.0f}%",
              delta=f"{(recycling - 0.9)*100:+.0f}%" if recycling != 0.9 else "nominal")

time.sleep(1)
st.rerun()
