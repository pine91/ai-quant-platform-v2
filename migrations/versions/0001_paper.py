"""Create persistent virtual balance and execution tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_paper"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_accounts",
        sa.Column("instrument", sa.String(100), primary_key=True),
        sa.Column("cash", sa.Numeric(28, 8), nullable=False),
        sa.Column("units", sa.Numeric(28, 8), nullable=False),
    )
    op.create_table(
        "paper_fills",
        sa.Column("instrument", sa.String(100), sa.ForeignKey("paper_accounts.instrument"), primary_key=True),
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Numeric(28, 8), nullable=False),
        sa.Column("price", sa.Numeric(28, 8), nullable=False),
        sa.Column("fee", sa.Numeric(28, 8), nullable=False),
        sa.Column("quote_time", sa.BigInteger, nullable=False),
        sa.Column("cash", sa.Numeric(28, 8), nullable=False),
        sa.Column("units", sa.Numeric(28, 8), nullable=False),
    )


def downgrade():
    op.drop_table("paper_fills")
    op.drop_table("paper_accounts")
