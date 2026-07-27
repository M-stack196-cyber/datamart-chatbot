"""Add conversation_state table (persists bot state + handoff mode) and
user online-status columns for the live handoff feature.

Revision ID: add_handoff_and_state
Revises: add_lead_tables
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_handoff_and_state'
down_revision = 'add_lead_tables'
branch_labels = None
depends_on = None


def upgrade():
    # conversation_state table - persists LeadCaptureAgent progress and
    # bot/human handoff mode across serverless requests.
    op.create_table(
        'conversation_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('lead_started', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('awaiting_field', sa.String(50), nullable=True),
        sa.Column('collected_data', sa.Text(), server_default='{}'),
        sa.Column('completed_fields', sa.Text(), server_default='[]'),
        sa.Column('optional_attempted', sa.Text(), server_default='[]'),
        sa.Column('skipped_fields', sa.Text(), server_default='[]'),
        sa.Column('mode', sa.String(20), nullable=False, server_default='bot'),
        sa.Column('assigned_agent_id', sa.Integer(), nullable=True),
        sa.Column('handoff_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id'),
    )
    op.create_index('ix_conversation_state_conversation_id', 'conversation_state', ['conversation_id'])
    op.create_index('ix_conversation_state_mode', 'conversation_state', ['mode'])

    # users: online/offline availability for live handoff
    op.add_column('users', sa.Column('is_online', sa.Boolean(), server_default=sa.text('false')))
    op.add_column('users', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'is_online')
    op.drop_index('ix_conversation_state_mode', table_name='conversation_state')
    op.drop_index('ix_conversation_state_conversation_id', table_name='conversation_state')
    op.drop_table('conversation_state')
