"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # tenants
    # ============================================
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('cuit', sa.String(length=11), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telefono', sa.String(length=50)),
        sa.Column('direccion', sa.Text()),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('plan', sa.String(length=50), server_default='profesional'),
        sa.Column('configuracion', sa.JSON(), server_default='{}'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('cuit'),
        sa.Index('ix_tenants_id', 'id'),
        sa.Index('ix_tenants_activo', 'activo'),
        sa.Index('ix_tenants_cuit', 'cuit'),
    )

    # ============================================
    # usuarios
    # ============================================
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('rol', sa.String(length=50), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('telefono', sa.String(length=50)),
        sa.Column('avatar_url', sa.Text()),
        sa.Column('ultimo_acceso', sa.DateTime(timezone=True)),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('ix_usuarios_id', 'id'),
        sa.Index('ix_usuarios_email', 'email'),
    )

    # ============================================
    # clientes
    # ============================================
    op.create_table(
        'clientes',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cuit', sa.String(length=11), nullable=False),
        sa.Column('razon_social', sa.String(length=255), nullable=False),
        sa.Column('nombre_fantasia', sa.String(length=255)),
        sa.Column('tipo_persona', sa.String(length=20), server_default='fisica'),
        sa.Column('tipo_responsable', sa.String(length=100)),
        sa.Column('email', sa.String(length=255)),
        sa.Column('telefono', sa.String(length=50)),
        sa.Column('domicilio', sa.Text()),
        sa.Column('localidad', sa.String(length=100)),
        sa.Column('provincia', sa.String(length=100)),
        sa.Column('codigo_postal', sa.String(length=20)),
        sa.Column('fecha_inicio_actividades', sa.Date()),
        sa.Column('categoria_monotributo', sa.String(length=5)),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('configuracion', sa.JSON(), server_default='{}'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('ix_clientes_id', 'id'),
        sa.Index('ix_clientes_cuit', 'cuit'),
        sa.UniqueConstraint('tenant_id', 'cuit', name='uq_tenant_cuit'),
    )

    # ============================================
    # comprobantes
    # ============================================
    op.create_table(
        'comprobantes',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='SET NULL')),
        sa.Column('tipo_comprobante', sa.String(length=3), nullable=False),
        sa.Column('punto_venta', sa.Integer(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('cuit_emisor', sa.String(length=11)),
        sa.Column('cuit_receptor', sa.String(length=11)),
        sa.Column('fecha_emision', sa.Date()),
        sa.Column('fecha_vencimiento', sa.Date()),
        sa.Column('fecha_servicio_desde', sa.Date()),
        sa.Column('fecha_servicio_hasta', sa.Date()),
        sa.Column('total', sa.Numeric(15, 2), nullable=False),
        sa.Column('neto_gravado', sa.Numeric(15, 2), server_default='0'),
        sa.Column('neto_exento', sa.Numeric(15, 2), server_default='0'),
        sa.Column('neto_no_gravado', sa.Numeric(15, 2), server_default='0'),
        sa.Column('iva', sa.Numeric(15, 2), server_default='0'),
        sa.Column('percepcion_iibb', sa.Numeric(15, 2), server_default='0'),
        sa.Column('percepcion_iva', sa.Numeric(15, 2), server_default='0'),
        sa.Column('percepcion_ganancias', sa.Numeric(15, 2), server_default='0'),
        sa.Column('cae', sa.String(length=50)),
        sa.Column('cae_vencimiento', sa.Date()),
        sa.Column('estado_arca', sa.String(length=50), server_default='PENDIENTE'),
        sa.Column('estado_arca_detalle', sa.Text()),
        sa.Column('fecha_consulta_arca', sa.DateTime(timezone=True)),
        sa.Column('estado_interno', sa.String(length=50), server_default='PENDIENTE_VERIFICACION'),
        sa.Column('hash_delta', sa.String(length=64), nullable=False),
        sa.Column('es_duplicado', sa.Boolean(), server_default='false'),
        sa.Column('duplicado_de', sa.Integer(), sa.ForeignKey('comprobantes.id')),
        sa.Column('origen', sa.String(length=50), server_default='manual'),
        sa.Column('archivo_original_id', sa.Integer()),
        sa.Column('observaciones', sa.Text()),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('modificado_por_usuario', sa.Integer(), sa.ForeignKey('usuarios.id')),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('ix_comprobantes_id', 'id'),
        sa.Index('ix_comprobantes_cuit_emisor', 'cuit_emisor'),
        sa.Index('ix_comprobantes_fecha_emision', 'fecha_emision'),
        sa.Index('ix_comprobantes_estado_arca', 'estado_arca'),
        sa.Index('ix_comprobantes_estado_interno', 'estado_interno'),
        sa.Index('ix_comprobantes_hash_delta', 'hash_delta'),
    )

    # ============================================
    # parametros_fiscales
    # ============================================
    op.create_table(
        'parametros_fiscales',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.JSON(), nullable=False),
        sa.Column('descripcion', sa.Text()),
        sa.Column('fecha_vigencia_desde', sa.Date(), nullable=False),
        sa.Column('fecha_vigencia_hasta', sa.Date()),
        sa.Column('fuente_normativa', sa.String(length=200)),
        sa.Column('creado_por', sa.Integer(), sa.ForeignKey('usuarios.id')),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('ix_parametros_fiscales_id', 'id'),
        sa.Index('ix_parametros_fiscales_nombre', 'nombre'),
        sa.Index('ix_parametros_fiscales_fecha_vigencia_desde', 'fecha_vigencia_desde'),
        sa.Index('ix_parametros_fiscales_fecha_vigencia_hasta', 'fecha_vigencia_hasta'),
    )

    # ============================================
    # veps
    # ============================================
    op.create_table(
        'veps',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='SET NULL')),
        sa.Column('tipo_vep', sa.String(length=50), nullable=False),
        sa.Column('periodo', sa.String(length=7), nullable=False),
        sa.Column('categoria', sa.String(length=10)),
        sa.Column('importe_original', sa.Numeric(15, 2), nullable=False),
        sa.Column('intereses', sa.Numeric(15, 2), server_default='0'),
        sa.Column('importe_total', sa.Numeric(15, 2), nullable=False),
        sa.Column('estado', sa.String(length=50), server_default='PRE_LIQUIDADO'),
        sa.Column('numero_vep', sa.String(length=50)),
        sa.Column('fecha_vencimiento', sa.Date()),
        sa.Column('aprobado_por', sa.Integer(), sa.ForeignKey('usuarios.id')),
        sa.Column('aprobado_en', sa.DateTime(timezone=True)),
        sa.Column('aprobacion_ip', sa.String(length=50)),
        sa.Column('aprobacion_user_agent', sa.Text()),
        sa.Column('fecha_pago', sa.Date()),
        sa.Column('comprobante_pago', sa.Text()),
        sa.Column('observaciones', sa.Text()),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('ix_veps_id', 'id'),
        sa.Index('ix_veps_periodo', 'periodo'),
        sa.Index('ix_veps_estado', 'estado'),
    )

    # ============================================
    # alertas
    # ============================================
    op.create_table(
        'alertas',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='SET NULL')),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='SET NULL')),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('severidad', sa.String(length=20), server_default='media'),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('leida', sa.Boolean(), server_default='false'),
        sa.Column('leida_en', sa.DateTime(timezone=True)),
        sa.Column('archivada', sa.Boolean(), server_default='false'),
        sa.Column('accion_requerida', sa.Text()),
        sa.Column('entidad_relacionada', sa.String(length=50)),
        sa.Column('id_relacionado', sa.Integer()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('ix_alertas_id', 'id'),
        sa.Index('ix_alertas_leida', 'leida'),
        sa.Index('ix_alertas_creado_en', 'creado_en'),
    )

    # ============================================
    # wsaa_tokens
    # ============================================
    op.create_table(
        'wsaa_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('servicio', sa.String(length=50), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('vencimiento', sa.DateTime(timezone=True), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('ix_wsaa_tokens_id', 'id'),
        sa.UniqueConstraint('tenant_id', 'servicio', name='uq_tenant_servicio'),
    )

    # ============================================
    # relaciones_arca
    # ============================================
    op.create_table(
        'relaciones_arca',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cuit_cliente', sa.String(length=11), nullable=False),
        sa.Column('servicios_delegados', sa.JSON(), server_default='[]'),
        sa.Column('activa', sa.Boolean(), server_default='true'),
        sa.Column('fecha_alta', sa.Date()),
        sa.Column('fecha_ultima_verificacion', sa.DateTime(timezone=True)),
        sa.Column('fecha_vencimiento_certificado', sa.Date()),
        sa.Column('verificada_ok', sa.Boolean(), server_default='false'),
        sa.Column('error_ultimo', sa.Text()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'cliente_id', name='uq_relacion_tenant_cliente'),
    )

    # ============================================
    # log_auditoria
    # ============================================
    op.create_table(
        'log_auditoria',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id')),
        sa.Column('accion', sa.String(length=100), nullable=False),
        sa.Column('entidad', sa.String(length=50)),
        sa.Column('entidad_id', sa.Integer()),
        sa.Column('payload_hash', sa.String(length=64)),
        sa.Column('resultado', sa.String(length=20)),
        sa.Column('detalle', sa.Text()),
        sa.Column('ip_origen', sa.String(length=50)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('timestamp_rfc3161', sa.Text()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index('ix_log_auditoria_id', 'id'),
        sa.Index('ix_log_auditoria_creado_en', 'creado_en'),
    )

    # ============================================
    # solicitudes_arco
    # ============================================
    op.create_table(
        'solicitudes_arco',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('cuit_solicitante', sa.String(length=11), nullable=False),
        sa.Column('nombre_solicitante', sa.String(length=255)),
        sa.Column('email_contacto', sa.String(length=255)),
        sa.Column('descripcion', sa.Text()),
        sa.Column('estado', sa.String(length=20), server_default='PENDIENTE'),
        sa.Column('fecha_respuesta', sa.DateTime(timezone=True)),
        sa.Column('motivo_denegacion', sa.Text()),
        sa.Column('datos_retenidos_por_ley', sa.JSON()),
        sa.Column('fecha_vencimiento_sla', sa.DateTime(timezone=True)),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ============================================
    # calendario_vencimientos
    # ============================================
    op.create_table(
        'calendario_vencimientos',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('organismo', sa.String(length=20), nullable=False),
        sa.Column('tipo_obligacion', sa.String(length=60), nullable=False),
        sa.Column('terminacion_cuit', sa.Integer()),
        sa.Column('categoria_monotributo', sa.String(length=5)),
        sa.Column('fecha_base', sa.Date(), nullable=False),
        sa.Column('fecha_efectiva', sa.Date()),
        sa.Column('es_prorroga', sa.Boolean(), server_default='false'),
        sa.Column('fuente', sa.String(length=200)),
        sa.Column('vigencia_desde', sa.Date(), nullable=False),
        sa.Column('vigencia_hasta', sa.Date()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('calendario_vencimientos')
    op.drop_table('solicitudes_arco')
    op.drop_table('log_auditoria')
    op.drop_table('relaciones_arca')
    op.drop_table('wsaa_tokens')
    op.drop_table('alertas')
    op.drop_table('veps')
    op.drop_table('parametros_fiscales')
    op.drop_table('comprobantes')
    op.drop_table('clientes')
    op.drop_table('usuarios')
    op.drop_table('tenants')
