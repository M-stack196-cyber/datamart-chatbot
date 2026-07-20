"""Add lead capture tables

Revision ID: add_lead_tables
Revises: 
Create Date: 2026-07-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_lead_tables'
down_revision = None  # Change this to your last migration if you have one
branch_labels = None
depends_on = None

def upgrade():
    # contact_info table
    op.create_table(
        'contact_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('project_description', sa.Text(), nullable=False),
        sa.Column('company', sa.String(150), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('project_title', sa.String(255), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('budget', sa.String(100), nullable=True),
        sa.Column('timeline', sa.String(100), nullable=True),
        sa.Column('preferred_contact_method', sa.String(20), nullable=True),
        sa.Column('source', sa.String(30), nullable=False, server_default='public_widget'),
        sa.Column('status', sa.String(30), nullable=False, server_default='new'),
        sa.Column('lead_score', sa.Integer(), default=0),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id')
    )
    
    # conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['contact_info.conversation_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # project_requests table
    op.create_table(
        'project_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_title', sa.String(255), nullable=False),
        sa.Column('project_description', sa.Text(), nullable=False),
        sa.Column('budget', sa.String(100), nullable=True),
        sa.Column('timeline', sa.String(100), nullable=True),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('is_urgent', sa.Boolean(), default=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # project_conversation table
    op.create_table(
        'project_conversation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['request_id'], ['project_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for performance
    op.create_index('idx_contact_email', 'contact_info', ['email'])
    op.create_index('idx_contact_status', 'contact_info', ['status'])
    op.create_index('idx_contact_created', 'contact_info', ['created_at'])
    op.create_index('idx_project_user', 'project_requests', ['user_id'])
    op.create_index('idx_project_status', 'project_requests', ['status'])
    op.create_index('idx_project_created', 'project_requests', ['created_at'])

def downgrade():
    op.drop_table('project_conversation')
    op.drop_table('project_requests')
    op.drop_table('conversation_history')
    op.drop_table('contact_info')