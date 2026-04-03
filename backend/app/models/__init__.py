"""
Modelos SQLAlchemy de AccountantOS
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric, Date, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


# ============================================
# MODELOS BASE
# ============================================

class TimestampMixin:
    """Mixin para timestamps automáticos"""
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================
# TENANT (Estudio Contable)
# ============================================

class Tenant(Base, TimestampMixin):
    """Estudio contable (tenant multi-tenant)"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    cuit = Column(String(11), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    telefono = Column(String(50))
    direccion = Column(Text)
    activo = Column(Boolean, default=True, index=True)
    plan = Column(String(50), default="profesional")
    configuracion = Column(JSON, default=dict)

    # Relaciones
    usuarios = relationship("Usuario", back_populates="tenant", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="tenant", cascade="all, delete-orphan")
    comprobantes = relationship("Comprobante", back_populates="tenant", cascade="all, delete-orphan")
    veps = relationship("VEP", back_populates="tenant", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="tenant", cascade="all, delete-orphan")


# ============================================
# USUARIO
# ============================================

class Usuario(Base, TimestampMixin):
    """Usuario del sistema"""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False)  # admin_estudio, operador_senior, operador, cliente
    activo = Column(Boolean, default=True)
    telefono = Column(String(50))
    avatar_url = Column(Text)
    ultimo_acceso = Column(DateTime(timezone=True))

    # Relaciones
    tenant = relationship("Tenant", back_populates="usuarios")


# ============================================
# CLIENTE
# ============================================

class Cliente(Base, TimestampMixin):
    """Cliente de un estudio contable"""

    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cuit = Column(String(11), nullable=False, index=True)
    razon_social = Column(String(255), nullable=False)
    nombre_fantasia = Column(String(255))
    tipo_persona = Column(String(20), default="fisica")
    tipo_responsable = Column(String(100))
    email = Column(String(255))
    telefono = Column(String(50))
    domicilio = Column(Text)
    localidad = Column(String(100))
    provincia = Column(String(100))
    codigo_postal = Column(String(20))
    fecha_inicio_actividades = Column(Date)
    categoria_monotributo = Column(String(5))
    activo = Column(Boolean, default=True)
    configuracion = Column(JSON, default=dict)

    # Relaciones
    tenant = relationship("Tenant", back_populates="clientes")
    comprobantes = relationship("Comprobante", back_populates="cliente")
    veps = relationship("VEP", back_populates="cliente")

    __table_args__ = (
        UniqueConstraint("tenant_id", "cuit", name="uq_tenant_cuit"),
    )


# ============================================
# COMPROBANTE
# ============================================

class Comprobante(Base, TimestampMixin):
    """Comprobante fiscal (factura, nota de crédito, etc.)"""

    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"))

    # Datos del comprobante
    tipo_comprobante = Column(String(3), nullable=False)
    punto_venta = Column(Integer, nullable=False)
    numero = Column(Integer, nullable=False)
    cuit_emisor = Column(String(11), index=True)
    cuit_receptor = Column(String(11))

    # Fechas
    fecha_emision = Column(Date, index=True)
    fecha_vencimiento = Column(Date)
    fecha_servicio_desde = Column(Date)
    fecha_servicio_hasta = Column(Date)

    # Importes
    total = Column(Numeric(15, 2), nullable=False)
    neto_gravado = Column(Numeric(15, 2), default=0)
    neto_exento = Column(Numeric(15, 2), default=0)
    neto_no_gravado = Column(Numeric(15, 2), default=0)
    iva = Column(Numeric(15, 2), default=0)
    percepcion_iibb = Column(Numeric(15, 2), default=0)
    percepcion_iva = Column(Numeric(15, 2), default=0)
    percepcion_ganancias = Column(Numeric(15, 2), default=0)

    # Estado en ARCA
    cae = Column(String(50))
    cae_vencimiento = Column(Date)
    estado_arca = Column(String(50), default="PENDIENTE", index=True)
    estado_arca_detalle = Column(Text)
    fecha_consulta_arca = Column(DateTime(timezone=True))

    # Procesamiento interno
    estado_interno = Column(String(50), default="PENDIENTE_VERIFICACION", index=True)
    hash_delta = Column(String(64), nullable=False, index=True)
    es_duplicado = Column(Boolean, default=False)
    duplicado_de = Column(Integer, ForeignKey("comprobantes.id"))

    # Origen
    origen = Column(String(50), default="manual")
    archivo_original_id = Column(Integer)

    # Metadata
    observaciones = Column(Text)
    datos_metadata = Column("metadata", JSON, default=dict)

    modificado_por_usuario = Column(Integer, ForeignKey("usuarios.id"))

    # Relaciones
    tenant = relationship("Tenant", back_populates="comprobantes")
    cliente = relationship("Cliente", back_populates="comprobantes")


# ============================================
# PARÁMETRO FISCAL
# ============================================

class ParametroFiscal(Base):
    """Parámetros fiscales versionados (categorías, alícuotas, etc.)"""

    __tablename__ = "parametros_fiscales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, index=True)
    valor = Column(JSON, nullable=False)
    descripcion = Column(Text)
    fecha_vigencia_desde = Column(Date, nullable=False, index=True)
    fecha_vigencia_hasta = Column(Date, index=True)
    fuente_normativa = Column(String(200))
    creado_por = Column(Integer, ForeignKey("usuarios.id"))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# VEP (Obligación Fiscal)
# ============================================

class VEP(Base, TimestampMixin):
    """VEP - Obligación fiscal pre-liquidada"""

    __tablename__ = "veps"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"))

    # Datos de la obligación
    tipo_vep = Column(String(50), nullable=False)
    periodo = Column(String(7), nullable=False, index=True)
    categoria = Column(String(10))
    importe_original = Column(Numeric(15, 2), nullable=False)
    intereses = Column(Numeric(15, 2), default=0)
    importe_total = Column(Numeric(15, 2), nullable=False)

    # Estado
    estado = Column(String(50), default="PRE_LIQUIDADO", index=True)
    numero_vep = Column(String(50))
    fecha_vencimiento = Column(Date)

    # Aprobación del cliente
    aprobado_por = Column(Integer, ForeignKey("usuarios.id"))
    aprobado_en = Column(DateTime(timezone=True))
    aprobacion_ip = Column(String(50))
    aprobacion_user_agent = Column(Text)

    # Pago
    fecha_pago = Column(Date)
    comprobante_pago = Column(Text)

    # Metadata
    observaciones = Column(Text)
    datos_metadata = Column("metadata", JSON, default=dict)

    # Relaciones
    tenant = relationship("Tenant", back_populates="veps")
    cliente = relationship("Cliente", back_populates="veps")


# ============================================
# ALERTA
# ============================================

class Alerta(Base):
    """Alertas y notificaciones del sistema"""

    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"))
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"))

    tipo = Column(String(50), nullable=False)
    severidad = Column(String(20), default="media")
    titulo = Column(String(255), nullable=False)
    mensaje = Column(Text, nullable=False)

    # Estado
    leida = Column(Boolean, default=False, index=True)
    leida_en = Column(DateTime(timezone=True))
    archivada = Column(Boolean, default=False)

    # Acción asociada
    accion_requerida = Column(Text)
    entidad_relacionada = Column(String(50))
    id_relacionado = Column(Integer)

    creado_en = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relaciones
    tenant = relationship("Tenant", back_populates="alertas")


# ============================================
# TOKEN WSAA
# ============================================

class WSAAToken(Base):
    """Tokens de autenticación WSAA (caché efímera)"""

    __tablename__ = "wsaa_tokens"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    servicio = Column(String(50), nullable=False)
    token = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)
    vencimiento = Column(DateTime(timezone=True), nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "servicio", name="uq_tenant_servicio"),
    )


# ============================================
# RELACIÓN ARCA (Delegación)
# ============================================

class RelacionARCA(Base, TimestampMixin):
    """Registra qué clientes tienen Relación Delegada activa en ARCA"""

    __tablename__ = "relaciones_arca"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    cuit_cliente = Column(String(11), nullable=False)
    servicios_delegados = Column(JSON, default=list)  # ["wsfe", "wscdc", "padron_a4"]
    activa = Column(Boolean, default=True)
    fecha_alta = Column(Date)
    fecha_ultima_verificacion = Column(DateTime(timezone=True))
    fecha_vencimiento_certificado = Column(Date)
    verificada_ok = Column(Boolean, default=False)
    error_ultimo = Column(Text)

    tenant = relationship("Tenant")
    cliente = relationship("Cliente")

    __table_args__ = (
        UniqueConstraint("tenant_id", "cliente_id", name="uq_relacion_tenant_cliente"),
    )


# ============================================
# LOG DE AUDITORÍA (append-only)
# ============================================

class LogAuditoria(Base):
    """Log inmutable de operaciones críticas — append-only"""

    __tablename__ = "log_auditoria"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    accion = Column(String(100), nullable=False)       # "WSFE_DESCARGA", "VEP_APROBADO", etc.
    entidad = Column(String(50))                        # "comprobante", "vep", "cliente"
    entidad_id = Column(Integer)

    # Hash del payload (nunca el payload real con datos sensibles)
    payload_hash = Column(String(64))                  # SHA-256 del request original
    resultado = Column(String(20))                     # "OK", "ERROR", "RECHAZADO"
    detalle = Column(Text)

    ip_origen = Column(String(50))
    user_agent = Column(Text)

    # Timestamp RFC 3161 (externo, para valor probatorio)
    timestamp_rfc3161 = Column(Text)                   # Respuesta del proveedor

    creado_en = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    tenant = relationship("Tenant")


# ============================================
# SOLICITUD ARCO (Ley 25.326)
# ============================================

class SolicitudARCO(Base, TimestampMixin):
    """Solicitudes ARCO (Acceso, Rectificación, Cancelación, Oposición) — Ley 25.326"""

    __tablename__ = "solicitudes_arco"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # ACCESO/RECTIFICACION/CANCELACION/OPOSICION
    cuit_solicitante = Column(String(11), nullable=False)
    nombre_solicitante = Column(String(255))
    email_contacto = Column(String(255))
    descripcion = Column(Text)

    estado = Column(String(20), default="PENDIENTE")  # PENDIENTE/COMPLETADA/DENEGADA_LEGAL
    fecha_respuesta = Column(DateTime(timezone=True))
    motivo_denegacion = Column(Text)
    datos_retenidos_por_ley = Column(JSON)  # Lista de campos que NO se pueden eliminar

    # SLA: 5 días hábiles (Ley 25.326)
    fecha_vencimiento_sla = Column(DateTime(timezone=True))

    tenant = relationship("Tenant")


# ============================================
# CALENDARIO DE VENCIMIENTOS FISCALES
# ============================================

class CalendarioVencimiento(Base):
    """Vencimientos fiscales multi-jurisdicción"""

    __tablename__ = "calendario_vencimientos"

    id = Column(Integer, primary_key=True)
    organismo = Column(String(20), nullable=False)       # ARCA, ARBA, AGIP, etc.
    tipo_obligacion = Column(String(60), nullable=False)  # IVA_MENSUAL, MONOTRIBUTO, etc.
    terminacion_cuit = Column(Integer)                    # 0-9 o NULL = todos
    categoria_monotributo = Column(String(5))             # NULL = aplica a todos

    fecha_base = Column(Date, nullable=False)
    fecha_efectiva = Column(Date)                         # Ajustada por feriados/prórrogas
    es_prorroga = Column(Boolean, default=False)
    fuente = Column(String(200))                          # "RG ARCA XXXX/2026"

    vigencia_desde = Column(Date, nullable=False)
    vigencia_hasta = Column(Date)                         # NULL = vigente

    creado_en = Column(DateTime(timezone=True), server_default=func.now())
