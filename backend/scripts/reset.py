"""Drops and recreates all tables, then reseeds - the literal "reset" half of
Sec. 11's "reset and replay" requirement, minimal version.

This only resets the database. It does NOT reset the running server's
in-memory Scenario Lab state (sim_controller/sim_clock) - this script runs as
its own separate process, so importing those modules here gets different
objects than whatever the live `uvicorn` process is holding. To actually clear
Scenario Lab overrides on a running server, call `POST /api/lab/reset`
instead - this script and that endpoint are two different kinds of "reset."
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine
from scripts.seed import run as seed


def run():
    Base.metadata.drop_all(bind=engine)
    seed()


if __name__ == "__main__":
    run()
