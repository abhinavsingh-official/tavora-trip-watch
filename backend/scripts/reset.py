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

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine
from scripts.seed import run as seed


def run():
    Base.metadata.drop_all(bind=engine)
    # alembic_version isn't part of Base.metadata (it's Alembic's own
    # tracking table, not one of our models) - drop_all leaves it behind
    # recording "already at head" even though the real tables are gone.
    # Without this, seed()'s `alembic upgrade head` would see nothing to do
    # and never recreate them. V7 adds real migrations - see
    # backend/alembic/.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    seed()


if __name__ == "__main__":
    run()
