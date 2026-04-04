"""add RLS policies for multi-tenant isolation

Revision ID: 002
Revises: 001
Create Date: 2026-04-03 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable Row-Level Security (RLS) on all tables with tenant_id.
    Only applies to PostgreSQL. SQLite does not support RLS.
    """
    # Detectar dialecto
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name != 'postgresql':
        # SQLite no soporta RLS. En dev usamos SQLite sin RLS.
        # En produccion (PostgreSQL) RLS se activa aqui.
        return

    tables_with_tenant = [
        "comprobantes",
        "clientes",
        "veps",
        "alertas",
        "wsaa_tokens",
        "relaciones_arca",
        "log_auditoria",
        "solicitudes_arco",
    ]

    op.execute(
        "DO $$ BEGIN"
        "  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='accountantos_app') THEN"
        "    CREATE ROLE accountantos_app;"
        "  END IF;"
        "END $$"
    )

    for tabla in tables_with_tenant:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {tabla}
            USING (tenant_id = current_setting('app.current_tenant', true)::int)
        """)

    for tabla in tables_with_tenant:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO accountantos_app")

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON usuarios TO accountantos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON parametros_fiscales TO accountantos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON calendario_vencimientos TO accountantos_app")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    tables_with_tenant = [
        "comprobantes",
        "clientes",
        "veps",
        "alertas",
        "wsaa_tokens",
        "relaciones_arca",
        "log_auditoria",
        "solicitudes_arco",
    ]

    for tabla in tables_with_tenant:
        op.execute(f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP ROLE IF EXISTS accountantos_app")
