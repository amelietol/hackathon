import time
import json
import os
from dataclasses import dataclass, asdict

@dataclass
class Astronaut:
    name: str
    health: float = 100.0
    hunger: float = 100.0  # 100 = full, 0 = starving

@dataclass
class Potato:
    hydration: float = 100.0  # 100 = fully hydrated, 0 = dead

@dataclass
class SimState:
    day: int = 0
    astronauts: list = None
    potato: Potato = None

    def __post_init__(self):
        if self.astronauts is None:
            self.astronauts = [
                Astronaut("Alex"),
                Astronaut("Jordan"),
                Astronaut("Sam"),
                Astronaut("Riley"),
            ]
        if self.potato is None:
            self.potato = Potato()

    def tick(self):
        self.day += 1
        self.potato.hydration = max(0.0, self.potato.hydration - 2.0)
        for a in self.astronauts:
            a.hunger = max(0.0, a.hunger - 5.0)
            if self.potato.hydration > 20.0 and a.hunger < 80.0:
                a.hunger = min(100.0, a.hunger + 15.0)
            if a.hunger < 20.0:
                a.health = max(0.0, a.health - 3.0)
            else:
                a.health = min(100.0, a.health + 0.5)

    def to_dict(self):
        return {
            "day": self.day,
            "astronauts": [asdict(a) for a in self.astronauts],
            "potato": asdict(self.potato),
        }

BASE = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE, "state.json")
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
    state.potato = Potato(**data["potato"])
    return state

def read_control() -> dict:
    if not os.path.exists(CONTROL_FILE):
        return {"paused": False, "reset": False}
    with open(CONTROL_FILE) as f:
        return json.load(f)

def write_control(paused: bool, reset: bool = False):
    with open(CONTROL_FILE, "w") as f:
        json.dump({"paused": paused, "reset": reset}, f)

def run(days: int = 450, tick_delay: float = 0.5):
    write_control(paused=False)
    state = load_state()
    print(f"Starting from day {state.day}")

    while state.day < days:
        ctrl = read_control()

        if ctrl.get("reset"):
            state = SimState()
            save_state(state)
            write_control(paused=False, reset=False)
            print("Simulation reset to day 0")
            continue

        if ctrl.get("paused"):
            time.sleep(0.2)
            continue

        state.tick()
        save_state(state)
        print(f"Day {state.day} | Potato: {state.potato.hydration:.1f}")
        time.sleep(tick_delay)

    print("Simulation complete.")

if __name__ == "__main__":
    run()
