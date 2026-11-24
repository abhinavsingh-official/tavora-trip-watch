"""add distance_km and per_km_rate_inr to synthetic cab options

Revision ID: f1a2b3c4d5e6
Revises: 0c8eb2c911f2
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '0c8eb2c911f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Same nullable-then-backfill-then-NOT-NULL pattern as e7a83d470075 -
    every existing row gets the same 30km representative transfer distance
    this directory has always implicitly assumed (see
    scripts/generate_synthetic_data.py), with per_km_rate_inr backed out
    from its current base price so the two numbers stay consistent with
    what's already live.
    """
    op.add_column('synthetic_cab_options', sa.Column('distance_km', sa.Float(), nullable=True))
    op.add_column('synthetic_cab_options', sa.Column('per_km_rate_inr', sa.Float(), nullable=True))
    op.execute('UPDATE synthetic_cab_options SET distance_km = 30.0')
    op.execute('UPDATE synthetic_cab_options SET per_km_rate_inr = ROUND((base_price_per_leg_inr / 30.0)::numeric, 2)')
    op.alter_column('synthetic_cab_options', 'distance_km', nullable=False)
    op.alter_column('synthetic_cab_options', 'per_km_rate_inr', nullable=False)


def downgrade() -> None:
    op.drop_column('synthetic_cab_options', 'per_km_rate_inr')
    op.drop_column('synthetic_cab_options', 'distance_km')
