"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Owning module: SET module_id BELOW (required).
Rollback/recovery notes: DESCRIBE HERE (required).
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

module_id = "PXX"

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
