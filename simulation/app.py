import time
import streamlit as st
from sim import (load_state, save_state, read_control, write_control,
                 SPECIES_KCAL_PER_100G, DAILY_CALORIE_NEED)

st.set_page_config(page_title="Mars Base Simulation", layout="wide")
st.title("🚀 Mars Base — Day Survival Simulation")

ctrl      = read_control()
is_paused = ctrl.get("paused", False)

c1, c2, c3, _ = st.columns([1, 1, 1, 4])
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
    if st.button("💧 Hydrate All"):
        state = load_state()
        for plant in state.plants:
            water_needed = plant.count * 0.5
            if state.resources.water_liters >= water_needed:
                state.resources.water_liters -= water_needed
                plant.hydration = min(100.0, plant.hydration + 10.0)
        save_state(state); st.rerun()

st.caption(f"{'⏸ Paused' if is_paused else '▶ Running'}")

state = load_state()
st.subheader(f"📅 Day {state.day} / 450")

st.markdown("### 👨‍🚀 Astronauts")
cols = st.columns(4)
for col, a in zip(cols, state.astronauts):
    with col:
        status = "💀 DEAD" if not a.isAlive else "✅ Alive"
        st.markdown(f"**{a.name}** — {status}")
        if not a.isAlive:
            st.error("Deceased")
            continue

        def bar(label, value, max_val=1.0):
            col.markdown(label)
            col.progress(min(1.0, max(0.0, value / max_val)))
            col.caption(f"{value/max_val*100:.1f}%")

        bar("🫀 Hydration",          a.hydrationLevel)
        bar("🧠 Cognitive",          a.cognitivePerformance)
        bar("🦴 Bone Health",        a.boneHealthScore)
        bar("🛡 Immune",             a.immuneScore)
        bar("🔬 Micronutrients",     a.micronutrientScore)

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

        if st.button("💧 Water", key=f"water_{idx}"):
            water_needed = plant.count * 0.5
            if state.resources.water_liters >= water_needed:
                state.resources.water_liters -= water_needed
                plant.hydration = min(100.0, plant.hydration + 10.0)
                save_state(state)
            st.rerun()

        if plant.is_harvestable():
            kg = plant.harvest_kg()
            if st.button(f"🌾 Harvest (~{kg:.1f} kg)", key=f"harvest_{idx}"):
                current = getattr(state.inventory, plant.name, 0.0)
                setattr(state.inventory, plant.name, round(current + kg, 3))
                plant.days_planted = 0
                save_state(state)
                st.rerun()
        else:
            st.button("🌾 Not ready", key=f"harvest_{idx}", disabled=True)

st.markdown("---")

st.markdown("### ⚙️ Resources")
rcols = st.columns(3)
with rcols[0]: st.metric("Water",        f"{state.resources.water_liters:.1f} L")
with rcols[1]: st.metric("Growing Area", f"{state.resources.growing_area_m2:.1f} m²")
with rcols[2]: st.metric("Energy",       f"{state.resources.energy_kwh:.1f} kWh")

time.sleep(1)
st.rerun()
