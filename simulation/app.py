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

st.title("🚀 Mars Base — Day Survival Simulation")

ctrl      = read_control()
is_paused = ctrl.get("paused", False)

c1, c2, _ = st.columns([1, 1, 6])
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

st.caption(f"{'⏸ Paused' if is_paused else '▶ Running'}")

state = load_state()
st.subheader(f"📅 Day {state.day} / 450")

st.markdown("### 👨‍🚀 Astronauts")
cols = st.columns(4)
for idx, (col, a) in enumerate(zip(cols, state.astronauts)):
    with col:
        status = "💀 DEAD" if not a.isAlive else ""
        st.markdown(f"<h4 style='text-align: center;'>{a.name} {status}</h4>", unsafe_allow_html=True)
        
        if not a.isAlive:
            st.error("Deceased")
        else:
            # Main health indicator - Micronutrients only (above image)
            st.markdown("🔬 Overall Health")
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
mc1, mc2, mc3, mc4 = st.columns(4)
with mc1: st.metric("🌡 External Temp",    f"{env.external_temp_c}°C")
with mc2: st.metric("🏠 Greenhouse Temp",  f"{env.greenhouse_temp_c}°C")
with mc3: st.metric("☀️ Solar Irradiance",  f"{env.solar_irradiance_wm2:.0f} W/m²",
                     delta=f"{(env.solar_irradiance_wm2/1361*100):.0f}% of Earth")
with mc4: st.metric("💡 Effective PAR",     f"{env.effective_par():.0f} µmol/m²/s")

mc5, mc6, mc7, mc8 = st.columns(4)
with mc5: st.metric("🪨 Gravity",          f"{env.gravity_factor*100:.0f}% Earth",
                     delta=f"{env.gravity_ms2:.2f} m/s²")
with mc6: st.metric("☢️ Radiation (inside)", f"{env.effective_radiation():.2f} mSv/day")
with mc7: st.metric("🫁 CO₂ (greenhouse)",  f"{env.greenhouse_co2_ppm:.0f} ppm")
with mc8: st.metric("🏭 Pressure (ext.)",   f"{env.external_pressure_mbar:.1f} mbar",
                     delta=f"{(env.external_pressure_mbar/1013*100):.1f}% of Earth")

time.sleep(1)
st.rerun()
