"""Initial schema with users, farms, and crop_cycles tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-07 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('preferred_language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('role', sa.String(length=20), server_default='FARMER', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 2. Create farms table
    op.create_table(
        'farms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('area', sa.Float(), nullable=False),
        sa.Column('soil_type', sa.String(length=100), nullable=False),
        sa.Column('irrigation', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_farms_id'), 'farms', ['id'], unique=False)
    op.create_index(op.f('ix_farms_user_id'), 'farms', ['user_id'], unique=False)

    # 3. Create crop_cycles table
    op.create_table(
        'crop_cycles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('crop', sa.String(length=100), nullable=False),
        sa.Column('variety', sa.String(length=100), nullable=True),
        sa.Column('sowing_date', sa.Date(), nullable=True),
        sa.Column('growth_stage', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crop_cycles_farm_id'), 'crop_cycles', ['farm_id'], unique=False)
    op.create_index(op.f('ix_crop_cycles_id'), 'crop_cycles', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crop_cycles_id'), table_name='crop_cycles')
    op.drop_index(op.f('ix_crop_cycles_farm_id'), table_name='crop_cycles')
    op.drop_table('crop_cycles')

    op.drop_index(op.f('ix_farms_user_id'), table_name='farms')
    op.drop_index(op.f('ix_farms_id'), table_name='farms')
    op.drop_table('farms')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
