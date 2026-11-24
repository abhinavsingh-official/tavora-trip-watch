"""Drops and recreates all tables, then reseeds.

This only resets the database, not the running server's in-memory Scenario
Lab state. This script is a separate process, so it can't touch whatever
objects the live uvicorn process is holding. To clear Scenario Lab overrides
on a running server, hit POST /api/lab/reset instead.
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine
from scripts.seed import run as seed


def run():
    Base.metadata.drop_all(bind=engine)
    # alembic_version isn't one of our models, so drop_all leaves it behind
    # still claiming we're at head. Without dropping it too, seed()'s
    # `upgrade head` would see nothing to do and skip recreating the tables.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    seed()


if __name__ == "__main__":
    run()
