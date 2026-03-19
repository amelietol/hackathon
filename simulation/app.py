import time
import json
import os
import streamlit as st
from sim import load_state, read_control, write_control, SimState

st.set_page_config(page_title="Mars Base Simulation", layout="wide")
st.title("🚀 Mars Base — Day Survival Simulation")

# Controls
ctrl = read_control()
is_paused = ctrl.get("paused", False)

col1, col2, col3, _ = st.columns([1, 1, 1, 3])
with col1:
    if is_paused:
        if st.button("▶️ Resume"):
            write_control(paused=False)
            st.rerun()
    else:
        if st.button("⏸️ Pause"):
            write_control(paused=True)
            st.rerun()

with col2:
    if st.button("🔄 Restart"):
        write_control(paused=False, reset=True)
        st.rerun()

with col3:
    if st.button("💧 Hydrate All Plants"):
        write_control(paused=is_paused, hydrate=True)
        st.rerun()

st.markdown(f"**Status:** {'⏸ Paused' if is_paused else '▶ Running'}")

placeholder = st.empty()

while True:
    state = load_state()

    with placeholder.container():
        st.subheader(f"📅 Day {state.day} / 450")

        st.markdown("### 👨‍🚀 Astronauts")
        cols = st.columns(4)
        for col, astronaut in zip(cols, state.astronauts):
            with col:
                st.markdown(f"**{astronaut.name}**")
                st.markdown("Health")
                st.progress(astronaut.health / 100.0)
                st.caption(f"{astronaut.health:.1f}%")
                st.markdown("Hunger")
                st.progress(astronaut.hunger / 100.0)
                st.caption(f"{astronaut.hunger:.1f}%")
                st.markdown("Mental Health")
                st.progress(astronaut.mental_health / 100.0)
                st.caption(f"{astronaut.mental_health:.1f}%")

        st.markdown("---")
        st.markdown("### 📦 Resources")
        res_cols = st.columns(3)
        with res_cols[0]:
            st.metric("Water", f"{state.resources.water_liters:.1f} L")
        with res_cols[1]:
            st.metric("Growing Area", f"{state.resources.growing_area_m2:.1f} m²")
        with res_cols[2]:
            st.metric("Energy", f"{state.resources.energy_kwh:.1f} kWh")
        
        st.markdown("---")
        st.markdown("### 🌱 Plants")
        total_plants = sum(p.count for p in state.plants)
        st.caption(f"Total plants: {total_plants}")
        plant_cols = st.columns(len(state.plants))
        for idx, (col, plant) in enumerate(zip(plant_cols, state.plants)):
            with col:
                # Get growth stage and color
                stage = plant.get_growth_stage()
                stage_colors = {
                    "seedling": "🔴",
                    "vegetative": "🟡", 
                    "mature": "🟢",
                    "wilting": "🟤"
                }
                stage_emoji = stage_colors.get(stage, "⚪")
                
                st.markdown(f"**{plant.name}** {stage_emoji}")
                st.caption(f"Count: {plant.count} | Day {plant.days_planted}/{plant.growth_cycle_days}")
                st.caption(f"Stage: {stage.capitalize()}")
                st.markdown("Hydration")
                st.progress(plant.hydration / 100.0)
                st.caption(f"{plant.hydration:.1f}%")
                if st.button(f"💧 Hydrate", key=f"hydrate_{idx}"):
                    write_control(paused=is_paused, hydrate=True, plant_index=idx)
                    st.rerun()

    time.sleep(1)
    st.rerun()
