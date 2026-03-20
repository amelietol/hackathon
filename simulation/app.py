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
            /* Make text black */
            h1, h2, h3, p, label, .stMarkdown, span, div {{
                color: #000000 !important;
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

set_background("hg.jpeg")

st.title("Mars Base — Day Survival Simulation")

ctrl      = read_control()
is_paused = ctrl.get("paused", False)

c1, c2, c3, c4, c5, c6, _ = st.columns([1, 1, 1.5, 1.5, 1.5, 1.5, 1])
with c1:
    if is_paused:
        if st.button("Resume"):
            write_control(paused=False); st.rerun()
    else:
        if st.button("Pause"):
            write_control(paused=True); st.rerun()
with c2:
    if st.button("Restart"):
        write_control(paused=False, reset=True); st.rerun()
with c3:
    state_peek = load_state()
    storm_active = state_peek.mars_env.dust_storm_active if hasattr(state_peek, 'mars_env') and state_peek.mars_env else False
    if storm_active:
        st.button("Storm Active [Medium]", disabled=True)
    else:
        if st.button("Dust Storm [Medium]"):
            write_control(paused=False, trigger_storm=True); st.rerun()
with c4:
    water_fail = state_peek.mars_env.water_failure_active if hasattr(state_peek, 'mars_env') and state_peek.mars_env else False
    if water_fail:
        st.button("Pump Down [High]", disabled=True)
    else:
        if st.button("Water Failure [High]"):
            write_control(paused=False, trigger_water_failure=True); st.rerun()
with c5:
    if st.button("Meteorite [High]"):
        write_control(paused=False, trigger_meteorite=True); st.rerun()
with c6:
    flare = state_peek.mars_env.solar_flare_active if hasattr(state_peek, 'mars_env') and state_peek.mars_env else False
    if flare:
        st.button("Flare Active [Low]", disabled=True)
    else:
        if st.button("Solar Flare [Low]"):
            write_control(paused=False, trigger_solar_flare=True); st.rerun()

st.caption(f"{'Paused' if is_paused else 'Running'}")

state = load_state()
st.subheader(f"Day {state.day} / 450")

# Dust storm warning banner
if hasattr(state, 'mars_env') and state.mars_env and state.mars_env.dust_storm_active:
    env = state.mars_env
    temp_now = env.effective_greenhouse_temp()
    temp_drop = env.greenhouse_temp_c - temp_now
    st.error(
        f"DUST STORM IN PROGRESS [Medium Impact] — {env.dust_storm_days_remaining} days remaining\n\n"
        f"Severity: {env.dust_storm_severity*100:.0f}% · "
        f"Greenhouse temp dropped from {env.greenhouse_temp_c:.0f}°C → {temp_now:.0f}°C (−{temp_drop:.0f}°C) · "
        f"Light: {env.effective_par():.0f} µmol/m²/s (normal: 450) · "
        f"Water recycling: {env.water_recycling_efficiency()*100:.0f}% (normal: 90%) · "
        f"Growth rate: {env.growth_modifier()*100:.0f}% (normal: 91%)"
    )

# Water recycling failure banner
if hasattr(state, 'mars_env') and state.mars_env and state.mars_env.water_failure_active:
    env = state.mars_env
    st.error(
        f"WATER RECYCLING FAILURE [High Impact] — {env.water_failure_days_remaining} days remaining\n\n"
        f"Pump malfunction! Recycling dropped from 90% → {env.water_recycling_efficiency()*100:.0f}% · "
        f"Water reserves draining faster — rationing critical"
    )

# Solar flare banner
if hasattr(state, 'mars_env') and state.mars_env and state.mars_env.solar_flare_active:
    env = state.mars_env
    st.error(
        f"SOLAR FLARE [Low Impact] — {env.solar_flare_days_remaining} days remaining\n\n"
        f"Radiation spike! Inside dose: {env.effective_radiation():.2f} mSv/day (normal: 0.20 mSv/day) · "
        f"Immune systems under heavy stress · Shielding partially overwhelmed"
    )

# Meteorite damage / repair indicator
env_check = state.mars_env
if state.resources.growing_area_m2 < 450.0 or (hasattr(env_check, 'repair_active') and env_check.repair_active):
    area_lost = max(0, 450.0 - state.resources.growing_area_m2)
    if env_check.repair_active:
        repair_name = next((a.name for a in state.astronauts if a.id == env_check.repair_astronaut_id), "Unknown")
        st.warning(
            f"☄️ METEORITE DAMAGE — 🔧 {repair_name} repairing ({env_check.repair_days_remaining} days left)\n\n"
            f"Restoring 5 m²/day · Current: {state.resources.growing_area_m2:.0f} m² → Target: {env_check.repair_area_target:.0f} m² · "
            f"⚠️ {repair_name} consuming 1.5× calories during EVA repair"
        )
    elif area_lost > 0:
        st.warning(
            f"METEORITE DAMAGE — {area_lost:.0f} m² of growing area destroyed\n\n"
            f"Remaining: {state.resources.growing_area_m2:.0f} m² of 450 m² · "
            f"Active crops: {len(state.plants)} · "
            f"Lost {area_lost/450.0*100:.0f}% of greenhouse capacity"
        )

st.markdown("## Astronauts")
cols = st.columns(4)
for idx, (col, a) in enumerate(zip(cols, state.astronauts)):
    with col:
        status = "💀 DEAD" if not a.isAlive else ""
        repair_tag = " 🔧" if (hasattr(state.mars_env, 'repair_active') and state.mars_env.repair_active and a.id == state.mars_env.repair_astronaut_id) else ""
        st.markdown(f"<h4 style='text-align: center;'>{a.name} {status}{repair_tag}</h4>", unsafe_allow_html=True)
        
        if not a.isAlive:
            st.error("Deceased")
        else:
            # Main health indicator - Micronutrients only (above image)
            st.markdown("Overall Health")
            # Create a green progress bar (less neon)
            health_value = min(1.0, max(0.0, a.micronutrientScore))
            st.markdown(f"""
                <div style="width: 100%; background-color: #ddd; border-radius: 5px;">
                    <div style="width: {health_value*100}%; background-color: #4CAF50; height: 20px; border-radius: 5px;"></div>
                </div>
            """, unsafe_allow_html=True)
            st.caption(f"{a.micronutrientScore*100:.1f}%")
        
        # Display astronaut image (cropped from top 20%)
        try:
            st.markdown("""
                <style>
                .astronaut-img img {
                    object-fit: cover;
                    object-position: 0% 100%;
                    height: 80%;
                    margin-top: 20%;
                }
                </style>
            """, unsafe_allow_html=True)
            st.image("astronaut.png", use_container_width=True)
        except:
            pass
        
        if not a.isAlive:
            continue

        # Expandable section for detailed health metrics (below image)
        with st.expander("View Details"):
            # Create vertical bars using custom HTML/CSS
            cols_health = st.columns(5)
            health_metrics = [
                ("Hydration", a.hydrationLevel),
                ("Cognitive", a.cognitivePerformance),
                ("Bone Health", a.boneHealthScore),
                ("Immune", a.immuneScore),
                ("Micronutrients", a.micronutrientScore)
            ]
            
            for col, (label, value) in zip(cols_health, health_metrics):
                with col:
                    percentage = min(100, max(0, value * 100))
                    st.markdown(f"""
                        <div style="text-align: center;">
                            <div style="height: 100px; width: 30px; background-color: #ddd; border-radius: 5px; margin: 0 auto; position: relative;">
                                <div style="position: absolute; bottom: 0; width: 100%; height: {percentage}%; background-color: #4CAF50; border-radius: 5px;"></div>
                            </div>
                            <p style="font-size: 12px; margin-top: 5px;">{label}</p>
                            <p style="font-size: 11px; color: gray;">{percentage:.1f}%</p>
                        </div>
                    """, unsafe_allow_html=True)

        if a.calorieDeficitAccumulated > 0:
            days_equiv = a.calorieDeficitAccumulated / a.dailyCalorieNeed
            st.caption(f"Calorie deficit: {days_equiv:.1f} day-equiv")
        if a.proteinDeficitAccumulated > 50:
            st.caption(f"Protein deficit: {a.proteinDeficitAccumulated:.0f}g")

        st.caption(f"Emergency food: {a.storedFoodCalories/a.dailyCalorieNeed:.1f} days left")

st.markdown("---")

st.markdown("## Food Inventory")
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

st.caption(f"Greenhouse food covers **{days_left:.1f}** days for {alive_count} astronauts")

st.markdown("---")

st.markdown("## Greenhouse")
stage_icon = {"seedling":"Seedling","vegetative":"Vegetative","mature":"Mature","wilting":"Wilting"}

if len(state.plants) == 0:
    st.caption("No crops planted yet.")
else:
    plant_cols = st.columns(len(state.plants))
    for idx, (col, plant) in enumerate(zip(plant_cols, state.plants)):
        with col:
            # Display plant image if available
            if plant.name == "Potato":
                try:
                    st.image("potato.png", use_container_width=True)
                except:
                    pass
            elif plant.name == "Beans":
                try:
                    st.image("beans.png", use_container_width=True)
                except:
                    pass
            elif plant.name == "Lettuce":
                try:
                    st.image("lettuce.png", use_container_width=True)
                except:
                    pass
            elif plant.name == "Radish":
                try:
                    st.image("radish.png", use_container_width=True)
                except:
                    pass
            elif plant.name == "Herbs":
                try:
                    st.image("herbs.png", use_container_width=True)
                except:
                    pass
            
            stage = plant.get_growth_stage()
            st.markdown(f"**{plant.name}** [{stage_icon.get(stage,'Unknown')}]")
            st.caption(f"Day {plant.days_planted}/{plant.growth_cycle_days}")
            st.caption(f"{plant.area_m2} m²")
            
            # Hydration first
            st.markdown("Hydration")
            st.progress(plant.hydration / 100.0)
            st.caption(f"{plant.hydration:.1f}%")
            
            # Segmented progress bar for growth stages - one segment per day
            progress = plant.days_planted / plant.growth_cycle_days
            total_days = plant.growth_cycle_days
            current_day = plant.days_planted
            
            # Calculate stage boundaries
            seedling_end = int(total_days * 0.25)
            vegetative_end = int(total_days * 0.75)
            
            st.markdown("Growth Progress")
            
            # Create individual day segments
            segments_html = '<div style="display: flex; gap: 1px; width: 100%; height: 20px;">'
            
            for day in range(total_days):
                # Determine color based on stage
                if day < seedling_end:
                    color = "#ff4444"  # Red for seedling
                elif day < vegetative_end:
                    color = "#ffcc00"  # Yellow for vegetative
                else:
                    color = "#4CAF50"  # Green for mature
                
                # Determine if this day is completed
                if day < current_day:
                    fill_color = color
                else:
                    fill_color = "#ddd"  # Gray for incomplete
                
                segments_html += f'<div style="flex: 1; background-color: {fill_color}; border-radius: 1px;"></div>'
            
            segments_html += '</div>'
            st.markdown(segments_html, unsafe_allow_html=True)
            st.caption(f"Day {current_day}/{total_days}")

            if plant.is_harvestable():
                kg = plant.harvest_kg()
                if st.button(f"Harvest (~{kg:.1f} kg)", key=f"harvest_{idx}"):
                    current = getattr(state.inventory, plant.name, 0.0)
                    setattr(state.inventory, plant.name, round(current + kg, 3))
                    plant.days_planted = 0
                    save_state(state)
                    st.rerun()

st.markdown("---")

st.markdown("## Resources")
rcols = st.columns(3)
with rcols[0]: st.metric("Water",        f"{state.resources.water_liters:.1f} L")
with rcols[1]: st.metric("Growing Area", f"{state.resources.growing_area_m2:.1f} m²")
with rcols[2]: st.metric("Energy",       f"{state.resources.energy_kwh:.1f} kWh")

st.markdown("---")

st.markdown("## Mars Environment")
env = state.mars_env
actual_temp = env.effective_greenhouse_temp()
actual_par = env.effective_par()

mc1, mc2, mc3, mc4 = st.columns(4)
with mc1: st.metric("External Temp",    f"{env.external_temp_c}°C")
with mc2:
    temp_delta = actual_temp - env.greenhouse_temp_c
    st.metric("Greenhouse Temp",  f"{actual_temp:.0f}°C",
              delta=f"{temp_delta:+.0f}°C" if temp_delta != 0 else "nominal")
with mc3: st.metric("Solar Irradiance",  f"{env.solar_irradiance_wm2:.0f} W/m²",
                     delta=f"{(env.solar_irradiance_wm2/1361*100):.0f}% of Earth")
with mc4:
    par_status = "reduced" if actual_par < 400 else "nominal"
    st.metric("Effective PAR",     f"{actual_par:.0f} µmol/m²/s",
              delta=par_status)

mc5, mc6, mc7, mc8 = st.columns(4)
with mc5: st.metric("Gravity",          f"{env.gravity_factor*100:.0f}% Earth",
                     delta=f"{env.gravity_ms2:.2f} m/s²")
with mc6:
    rad = env.effective_radiation()
    rad_status = "FLARE 5x" if env.solar_flare_active else "nominal"
    st.metric("Radiation (inside)", f"{rad:.2f} mSv/day",
              delta=rad_status)
with mc7: st.metric("CO2 (greenhouse)",  f"{env.greenhouse_co2_ppm:.0f} ppm")
with mc8:
    recycling = env.water_recycling_efficiency()
    if env.water_failure_active:
        rec_delta = "PUMP FAIL"
    elif recycling != 0.9:
        rec_delta = f"{(recycling - 0.9)*100:+.0f}%"
    else:
        rec_delta = "nominal"
    st.metric("Water Recycling",   f"{recycling*100:.0f}%",
              delta=rec_delta)

time.sleep(1)
st.rerun()
