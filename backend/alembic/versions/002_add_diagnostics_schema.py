"""Add diagnoses table for crop disease and pest diagnostics

Revision ID: 002_add_diagnostics_schema
Revises: 001_initial_schema
Create Date: 2026-10-11 21:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_diagnostics_schema'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'diagnoses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('crop_cycle_id', sa.Integer(), nullable=False),
        sa.Column('image_path', sa.String(length=500), nullable=False),
        sa.Column('image_filename', sa.String(length=255), nullable=False),
        sa.Column('image_hash', sa.String(length=64), nullable=False),
        sa.Column('crop_name', sa.String(length=100), nullable=False),
        sa.Column('disease_name_en', sa.String(length=255), nullable=True),
        sa.Column('disease_name_mr', sa.String(length=255), nullable=True),
        sa.Column('pathogen_type', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('affected_area_percentage', sa.Float(), nullable=True),
        sa.Column('symptoms_en', sa.Text(), nullable=True),
        sa.Column('symptoms_mr', sa.Text(), nullable=True),
        sa.Column('recommendations_en', sa.Text(), nullable=True),
        sa.Column('recommendations_mr', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('soil_moisture', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['crop_cycle_id'], ['crop_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diagnoses_id'), 'diagnoses', ['id'], unique=False)
    op.create_index(op.f('ix_diagnoses_user_id'), 'diagnoses', ['user_id'], unique=False)
    op.create_index(op.f('ix_diagnoses_crop_cycle_id'), 'diagnoses', ['crop_cycle_id'], unique=False)
    op.create_index(op.f('ix_diagnoses_image_hash'), 'diagnoses', ['image_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_diagnoses_image_hash'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_crop_cycle_id'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_user_id'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_id'), table_name='diagnoses')
    op.drop_table('diagnoses')
