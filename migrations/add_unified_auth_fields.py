"""Database migration to add unified authentication fields to users table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'unified_auth_001'
down_revision = None  # Replace with your last migration revision
branch_labels = None
depends_on = None


def upgrade():
    """Add unified authentication fields to users table."""
    
    # Create AuthType enum
    auth_type_enum = postgresql.ENUM('email', 'wallet', 'hybrid', name='authtype')
    auth_type_enum.create(op.get_bind())
    
    # Add new columns
    op.add_column('users', sa.Column('auth_type', auth_type_enum, nullable=False, server_default='email'))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('wallet_verified', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update network column to have default value
    op.alter_column('users', 'network', server_default='ethereum')
    
    # Drop old unique constraint on wallet_address + network
    op.drop_constraint('uq_wallet_network', 'users', type_='unique')
    
    # Create new unique constraint on wallet_address only
    op.create_unique_constraint('uq_user_wallet', 'users', ['wallet_address'])
    
    # Add new index on auth_type
    op.create_index('idx_auth_type', 'users', ['auth_type'])
    
    # Update existing users' auth_type based on their current data
    connection = op.get_bind()
    
    # Set auth_type to 'wallet' for users with wallet_address but no email
    connection.execute(
        sa.text("""
        UPDATE users 
        SET auth_type = 'wallet', wallet_verified = true 
        WHERE wallet_address IS NOT NULL AND email IS NULL
        """)
    )
    
    # Set auth_type to 'hybrid' for users with both email and wallet_address
    connection.execute(
        sa.text("""
        UPDATE users 
        SET auth_type = 'hybrid', wallet_verified = true 
        WHERE wallet_address IS NOT NULL AND email IS NOT NULL
        """)
    )
    
    # Set auth_type to 'email' for users with email but no wallet_address (default is already 'email')
    # No action needed as default is already 'email'


def downgrade():
    """Remove unified authentication fields from users table."""
    
    # Drop new index
    op.drop_index('idx_auth_type', 'users')
    
    # Drop new unique constraint
    op.drop_constraint('uq_user_wallet', 'users', type_='unique')
    
    # Recreate old unique constraint
    op.create_unique_constraint('uq_wallet_network', 'users', ['wallet_address', 'network'])
    
    # Remove default from network column
    op.alter_column('users', 'network', server_default=None)
    
    # Drop new columns
    op.drop_column('users', 'wallet_verified')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'auth_type')
    
    # Drop AuthType enum
    auth_type_enum = postgresql.ENUM('email', 'wallet', 'hybrid', name='authtype')
    auth_type_enum.drop(op.get_bind())