"""Add heatmap_path and advisory_status columns to diagnoses table

Revision ID: 003_add_diagnostic_metadata
Revises: 002_add_diagnostics_schema
Create Date: 2026-10-25 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_diagnostic_metadata'
down_revision: Union[str, None] = '002_add_diagnostics_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('heatmap_path', sa.String(length=500), nullable=True))
    op.add_column('diagnoses', sa.Column('advisory_status', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'advisory_status')
    op.drop_column('diagnoses', 'heatmap_path')
