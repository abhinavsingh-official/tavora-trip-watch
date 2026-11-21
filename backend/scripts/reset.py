"""Drops and recreates all tables, then reseeds - the literal "reset" half of
Sec. 11's "reset and replay" requirement, minimal version. Also clears the
in-memory Scenario Lab state (sim_controller/sim_clock) so a reset is a true
clean slate, not just a database wipe.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller
from scripts.seed import run as seed


def run():
    Base.metadata.drop_all(bind=engine)
    sim_controller.reset()
    sim_clock.reset()
    seed()


if __name__ == "__main__":
    run()
