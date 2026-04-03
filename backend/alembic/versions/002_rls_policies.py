"""add RLS policies for multi-tenant isolation

Revision ID: 002
Revises: 001
Create Date: 2026-04-03 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable Row-Level Security (RLS) on all tables with tenant_id.
    
    The application sets the tenant context via:
        SELECT set_config('app.current_tenant', :tid, true)
    
    BEFORE any query. This policy ensures that each tenant
    can ONLY access its own data.
    """
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

    # Create the application role that does NOT bypass RLS
    op.execute(
        "DO $$ BEGIN"
        "  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='accountantos_app') THEN"
        "    CREATE ROLE accountantos_app;"
        "  END IF;"
        "END $$"
    )

    for tabla in tables_with_tenant:
        # Enable RLS
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")

        # Create tenant isolation policy
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {tabla}
            USING (tenant_id = current_setting('app.current_tenant', true)::int)
        """)

    # Grant permissions to the app role
    for tabla in tables_with_tenant:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO accountantos_app")

    # Also grant on existing tables without tenant_id
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON usuarios TO accountantos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON parametros_fiscales TO accountantos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON calendario_vencimientos TO accountantos_app")


def downgrade() -> None:
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
