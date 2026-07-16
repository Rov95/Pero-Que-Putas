"""agrega enunciado a preguntas

Revision ID: b3d1c07a52e4
Revises: 8ff28e7da4d6
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d1c07a52e4'
down_revision: Union[str, Sequence[str], None] = '8ff28e7da4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default temporal: rellena las filas existentes; luego se elimina
    # para que el modelo (sin default) y la base queden alineados.
    op.add_column(
        'preguntas',
        sa.Column('enunciado', sa.Text(), nullable=False, server_default='¿Qué prefieres?'),
    )
    op.alter_column('preguntas', 'enunciado', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('preguntas', 'enunciado')
