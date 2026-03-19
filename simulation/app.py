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

col1, col2, _ = st.columns([1, 1, 4])
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

        st.markdown("---")
        st.markdown("### 🥔 Potato Plant")
        pcol, _ = st.columns([1, 3])
        with pcol:
            st.markdown("Hydration")
            st.progress(state.potato.hydration / 100.0)
            st.caption(f"{state.potato.hydration:.1f}%")

    time.sleep(1)
    st.rerun()
