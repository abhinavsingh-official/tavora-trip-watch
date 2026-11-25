"""per-component holds on notifications, is_simulated flag on users

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Replaces the single shared `held_until` with one hold per component (flight/hotel/cab each
    expire on their own schedule - see monitoring.py's COMPONENT_HOLD_MINUTES), and flags the
    Simulation page's "Scenario" user so sim_clock fast-forwards only that sandbox, not the real
    demo users too.
    """
    op.add_column('notifications', sa.Column('held_until_flight', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('held_until_hotel', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('held_until_cab', sa.DateTime(timezone=True), nullable=True))
    op.execute(
        'UPDATE notifications SET held_until_flight = held_until, held_until_hotel = held_until, '
        'held_until_cab = held_until WHERE held_until IS NOT NULL'
    )
    op.drop_column('notifications', 'held_until')

    op.add_column('users', sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE users SET is_simulated = true WHERE name = 'Scenario'")


def downgrade() -> None:
    op.drop_column('users', 'is_simulated')

    op.add_column('notifications', sa.Column('held_until', sa.DateTime(timezone=True), nullable=True))
    op.execute('UPDATE notifications SET held_until = held_until_flight WHERE held_until_flight IS NOT NULL')
    op.drop_column('notifications', 'held_until_cab')
    op.drop_column('notifications', 'held_until_hotel')
    op.drop_column('notifications', 'held_until_flight')
