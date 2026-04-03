-- ============================================
-- ACCOUNTANTOS v9.7 - Inicialización de BD
-- ============================================

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- FUNCIONES DE UTILIDAD
-- ============================================

-- Función para obtener parámetro fiscal vigente en una fecha
CREATE OR REPLACE FUNCTION get_parametro_vigente(
    p_nombre VARCHAR(100),
    p_fecha DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT valor
    INTO result
    FROM parametros_fiscales
    WHERE nombre = p_nombre
      AND p_fecha >= fecha_vigencia_desde
      AND (fecha_vigencia_hasta IS NULL OR p_fecha <= fecha_vigencia_hasta)
    ORDER BY fecha_vigencia_desde DESC
    LIMIT 1;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TABLA DE AUDITORÍA (Todos los cambios)
-- ============================================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    tabla_nombre VARCHAR(100) NOT NULL,
    registro_id BIGINT NOT NULL,
    accion VARCHAR(20) NOT NULL CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE')),
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    user_id BIGINT,
    user_email VARCHAR(255),
    tenant_id BIGINT,
    ip_address INET,
    user_agent TEXT,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_tabla_registro ON audit_log(tabla_nombre, registro_id);
CREATE INDEX idx_audit_log_creado_en ON audit_log(creado_en DESC);

-- ============================================
-- TENANTS (Estudios Contables)
-- ============================================
CREATE TABLE tenants (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    cuit VARCHAR(11) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    telefono VARCHAR(50),
    direccion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    plan VARCHAR(50) DEFAULT 'profesional', -- basico, profesional, enterprise
    fecha_alta TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_baja TIMESTAMP WITH TIME ZONE,
    configuracion JSONB DEFAULT '{}',
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenants_cuit ON tenants(cuit);
CREATE INDEX idx_tenants_activo ON tenants(activo) WHERE activo = TRUE;

-- Trigger para actualizar actualizado_en
CREATE OR REPLACE FUNCTION update_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_actualizado_en
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_actualizado_en();

-- ============================================
-- USUARIOS
-- ============================================
CREATE TABLE usuarios (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL, -- admin_estudio, operador_senior, operador, cliente
    activo BOOLEAN DEFAULT TRUE,
    telefono VARCHAR(50),
    avatar_url TEXT,
    ultimo_acceso TIMESTAMP WITH TIME ZONE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_usuarios_tenant ON usuarios(tenant_id);
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_activo ON usuarios(activo) WHERE activo = TRUE;

CREATE TRIGGER trg_usuarios_actualizado_en
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_actualizado_en();

-- ============================================
-- CLIENTES (de cada estudio)
-- ============================================
CREATE TABLE clientes (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    cuit VARCHAR(11) NOT NULL,
    razon_social VARCHAR(255) NOT NULL,
    nombre_fantasia VARCHAR(255),
    tipo_persona VARCHAR(20) DEFAULT 'fisica', -- fisica, juridica
    tipo_responsable VARCHAR(100), -- Responsable Inscripto, Monotributista, etc.
    email VARCHAR(255),
    telefono VARCHAR(50),
    domicilio TEXT,
    localidad VARCHAR(100),
    provincia VARCHAR(100),
    codigo_postal VARCHAR(20),
    fecha_inicio_actividades DATE,
    categoria_monotributo VARCHAR(5),
    activo BOOLEAN DEFAULT TRUE,
    configuracion JSONB DEFAULT '{}',
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, cuit)
);

CREATE INDEX idx_clientes_tenant ON clientes(tenant_id);
CREATE INDEX idx_clientes_cuit ON clientes(cuit);
CREATE INDEX idx_clientes_activo ON clientes(activo) WHERE activo = TRUE;

CREATE TRIGGER trg_clientes_actualizado_en
    BEFORE UPDATE ON clientes
    FOR EACH ROW
    EXECUTE FUNCTION update_actualizado_en();

-- ============================================
-- PARÁMETROS FISCALES (Versionados)
-- ============================================
CREATE TABLE parametros_fiscales (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    valor JSONB NOT NULL,
    descripcion TEXT,
    fecha_vigencia_desde DATE NOT NULL,
    fecha_vigencia_hasta DATE,
    creado_por BIGINT REFERENCES usuarios(id),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parametros_nombre ON parametros_fiscales(nombre);
CREATE INDEX idx_parametros_vigencia ON parametros_fiscales(fecha_vigencia_desde, fecha_vigencia_hasta);

-- ============================================
-- COMPROBANTES
-- ============================================
CREATE TABLE comprobantes (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,

    -- Datos del comprobante
    tipo_comprobante VARCHAR(3) NOT NULL, -- 1=FA A, 6=FA B, etc.
    punto_venta INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    cuit_emisor VARCHAR(11),
    cuit_receptor VARCHAR(11),

    -- Fechas
    fecha_emision DATE,
    fecha_vencimiento DATE,
    fecha_servicio_desde DATE,
    fecha_servicio_hasta DATE,

    -- Importes
    total DECIMAL(15,2) NOT NULL,
    neto_gravado DECIMAL(15,2) DEFAULT 0,
    neto_exento DECIMAL(15,2) DEFAULT 0,
    neto_no_gravado DECIMAL(15,2) DEFAULT 0,
    iva DECIMAL(15,2) DEFAULT 0,
    percepcion_iibb DECIMAL(15,2) DEFAULT 0,
    percepcion_iva DECIMAL(15,2) DEFAULT 0,
    percepcion_ganancias DECIMAL(15,2) DEFAULT 0,

    -- Estado en ARCA
    cae VARCHAR(50),
    cae_vencimiento DATE,
    estado_arca VARCHAR(50) DEFAULT 'PENDIENTE', -- PRESENTE_VALIDO, PRESENTE_ANULADO, RECHAZADO, AUSENTE, etc.
    estado_arca_detalle TEXT,
    fecha_consulta_arca TIMESTAMP WITH TIME ZONE,

    -- Procesamiento interno
    estado_interno VARCHAR(50) DEFAULT 'PENDIENTE_VERIFICACION',
    hash_delta VARCHAR(64) NOT NULL, -- hash(cuit+punto_venta+numero) para lock distribuido
    es_duplicado BOOLEAN DEFAULT FALSE,
    duplicado_de BIGINT REFERENCES comprobantes(id),

    -- Origen
    origen VARCHAR(50) DEFAULT 'manual', -- manual, ocr, ws_cdc, importacion
    archivo_original_id BIGINT, -- referencia a archivos adjuntos

    -- Metadata
    observaciones TEXT,
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modificado_por_usuario BIGINT REFERENCES usuarios(id)
);

CREATE INDEX idx_comprobantes_tenant ON comprobantes(tenant_id);
CREATE INDEX idx_comprobantes_cliente ON comprobantes(cliente_id);
CREATE INDEX idx_comprobantes_cuit_emisor ON comprobantes(cuit_emisor);
CREATE INDEX idx_comprobantes_hash_delta ON comprobantes(hash_delta);
CREATE INDEX idx_comprobantes_estado_arca ON comprobantes(estado_arca);
CREATE INDEX idx_comprobantes_fecha_emision ON comprobantes(fecha_emision);
CREATE INDEX idx_comprobantes_pendientes ON comprobantes(estado_interno) WHERE estado_interno = 'PENDIENTE_VERIFICACION';

-- Índice único para evitar duplicados a nivel de base de datos
CREATE UNIQUE INDEX idx_comprobantes_unico
    ON comprobantes(tenant_id, cuit_emisor, punto_venta, numero)
    WHERE estado_interno != 'ANULADO';

CREATE TRIGGER trg_comprobantes_actualizado_en
    BEFORE UPDATE ON comprobantes
    FOR EACH ROW
    EXECUTE FUNCTION update_actualizado_en();

-- ============================================
-- ARCHIVOS ADJUNTOS (PDFs, imágenes, XML)
-- ============================================
CREATE TABLE archivos_adjuntos (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    comprobante_id BIGINT REFERENCES comprobantes(id) ON DELETE SET NULL,
    tipo VARCHAR(50) NOT NULL, -- factura_pdf, factura_xml, ocr_original
    nombre_original VARCHAR(255),
    mimetype VARCHAR(100),
    tamanio_bytes BIGINT,
    storage_path TEXT NOT NULL, -- ruta en S3 o filesystem
    checksum_sha256 VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}',
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_adjuntos_tenant ON archivos_adjuntos(tenant_id);
CREATE INDEX idx_adjuntos_comprobante ON archivos_adjuntos(comprobante_id);

-- ============================================
-- TOKENS WSAA (Caché efímera)
-- ============================================
CREATE TABLE wsaa_tokens (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    servicio VARCHAR(50) NOT NULL, -- wsfe, wsfex, wscdc, etc.
    token TEXT NOT NULL,
    signature TEXT NOT NULL,
    vencimiento TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Los tokens viejos se eliminan por TTL, no necesitamos índice especial
CREATE INDEX idx_wsaa_tenant_servicio ON wsaa_tokens(tenant_id, servicio);

-- ============================================
-- VEPs (Obligaciones Fiscales)
-- ============================================
CREATE TABLE veps (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,

    -- Datos de la obligación
    tipo_vep VARCHAR(50) NOT NULL, -- monotributo, ganancias, iva, etc.
    periodo VARCHAR(7) NOT NULL, -- YYYY-MM
    categoria VARCHAR(10), -- para monotributo
    importe_original DECIMAL(15,2) NOT NULL,
    intereses DECIMAL(15,2) DEFAULT 0,
    importe_total DECIMAL(15,2) NOT NULL,

    -- Estado
    estado VARCHAR(50) DEFAULT 'PRE_LIQUIDADO', -- PRE_LIQUIDADO, PENDIENTE_APROBACION, APROBADO, PAGADO, RECHAZADO
    numero_vep VARCHAR(50), -- número en ARCA
    fecha_vencimiento DATE,

    -- Aprobación del cliente
    aprobado_por BIGINT REFERENCES usuarios(id),
    aprobado_en TIMESTAMP WITH TIME ZONE,
    aprobacion_ip INET,
    aprobacion_user_agent TEXT,

    -- Pago
    fecha_pago DATE,
    comprobante_pago TEXT, -- URL o path al comprobante

    -- Metadata
    observaciones TEXT,
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_veps_tenant ON veps(tenant_id);
CREATE INDEX idx_veps_cliente ON veps(cliente_id);
CREATE INDEX idx_veps_periodo ON veps(periodo);
CREATE INDEX idx_veps_estado ON veps(estado);

CREATE TRIGGER trg_veps_actualizado_en
    BEFORE UPDATE ON veps
    FOR EACH ROW
    EXECUTE FUNCTION update_actualizado_en();

-- ============================================
-- ALERTAS Y NOTIFICACIONES
-- ============================================
CREATE TABLE alertas (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT REFERENCES tenants(id) ON DELETE CASCADE,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    cliente_id BIGINT REFERENCES clientes(id) ON DELETE SET NULL,

    tipo VARCHAR(50) NOT NULL, -- riesgo_fiscal, vencimiento, error_arca, duplicado, etc.
    severidad VARCHAR(20) DEFAULT 'media', -- baja, media, alta, critica
    titulo VARCHAR(255) NOT NULL,
    mensaje TEXT NOT NULL,

    -- Estado
    leida BOOLEAN DEFAULT FALSE,
    leida_en TIMESTAMP WITH TIME ZONE,
    archivada BOOLEAN DEFAULT FALSE,

    -- Acción asociada
    accion_requerida TEXT,
    entidad_relacionada VARCHAR(50), -- comprobante, vep, cliente
    id_relacionado BIGINT,

    -- Timestamps
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alertas_tenant ON alertas(tenant_id);
CREATE INDEX idx_alertas_usuario ON alertas(usuario_id);
CREATE INDEX idx_alertas_leida ON alertas(leida) WHERE leida = FALSE;
CREATE INDEX idx_alertas_creado_en ON alertas(creado_en DESC);

-- ============================================
-- SESIONES Y TOKENS DE REFRESCO
-- ============================================
CREATE TABLE sesiones (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE CASCADE NOT NULL,
    token_refresh_hash VARCHAR(64) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expira_en TIMESTAMP WITH TIME ZONE NOT NULL,
    revocado BOOLEAN DEFAULT FALSE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sesiones_usuario ON sesiones(usuario_id);
CREATE INDEX idx_sesiones_token ON sesiones(token_refresh_hash);
CREATE INDEX idx_sesiones_expira ON sesiones(expira_en);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
-- Habilitar RLS en todas las tablas multi-tenant
-- FORCE RLS previene bypass incluso para superusers

ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes FORCE ROW LEVEL SECURITY;

ALTER TABLE comprobantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE comprobantes FORCE ROW LEVEL SECURITY;

ALTER TABLE archivos_adjuntos ENABLE ROW LEVEL SECURITY;
ALTER TABLE archivos_adjuntos FORCE ROW LEVEL SECURITY;

ALTER TABLE veps ENABLE ROW LEVEL SECURITY;
ALTER TABLE veps FORCE ROW LEVEL SECURITY;

ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas FORCE ROW LEVEL SECURITY;

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios FORCE ROW LEVEL SECURITY;

ALTER TABLE sesiones ENABLE ROW LEVEL SECURITY;
ALTER TABLE sesiones FORCE ROW LEVEL SECURITY;

-- Política para clientes
CREATE POLICY clientes_tenant_isolation ON clientes
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para comprobantes
CREATE POLICY comprobantes_tenant_isolation ON comprobantes
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para archivos_adjuntos
CREATE POLICY archivos_adjuntos_tenant_isolation ON archivos_adjuntos
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para veps
CREATE POLICY veps_tenant_isolation ON veps
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para alertas
CREATE POLICY alertas_tenant_isolation ON alertas
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para usuarios (aislamiento por tenant)
CREATE POLICY usuarios_tenant_isolation ON usuarios
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- Política para sesiones (solo usuarios del tenant activo)
CREATE POLICY sesiones_tenant_isolation ON sesiones
    USING (
        usuario_id IN (
            SELECT id FROM usuarios
            WHERE tenant_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT
        )
    );

-- Política para tenants (solo ver su propio tenant)
CREATE POLICY tenants_self_access ON tenants
    USING (id = NULLIF(current_setting('app.current_tenant', TRUE), '')::BIGINT);

-- ============================================
-- DATOS INICIALES - Parámetros Fiscales 2026
-- ============================================

-- Categorías de Monotributo 2026 (valores estimados - actualizar según corresponda)
INSERT INTO parametros_fiscales (nombre, valor, descripcion, fecha_vigencia_desde)
VALUES
('monotributo_categorias_2026', '{
    "A": {"ingresos_brutos_anual": 1800000, "alquileres_anual": 126000, "precio_unitario_max": 55000},
    "B": {"ingresos_brutos_anual": 3600000, "alquileres_anual": 252000, "precio_unitario_max": 55000},
    "C": {"ingresos_brutos_anual": 5400000, "alquileres_anual": 378000, "precio_unitario_max": 55000},
    "D": {"ingresos_brutos_anual": 7200000, "alquileres_anual": 504000, "precio_unitario_max": 55000},
    "E": {"ingresos_brutos_anual": 9000000, "alquileres_anual": 630000, "precio_unitario_max": 55000},
    "F": {"ingresos_brutos_anual": 10800000, "alquileres_anual": 756000, "precio_unitario_max": 55000},
    "G": {"ingresos_brutos_anual": 12600000, "alquileres_anual": 882000, "precio_unitario_max": 55000},
    "H": {"ingresos_brutos_anual": 14400000, "alquileres_anual": 1008000, "precio_unitario_max": 55000},
    "I": {"ingresos_brutos_anual": 16200000, "alquileres_anual": 1134000, "precio_unitario_max": 55000},
    "J": {"ingresos_brutos_anual": 18000000, "alquileres_anual": 1260000, "precio_unitario_max": 55000},
    "K": {"ingresos_brutos_anual": 19800000, "alquileres_anual": 1386000, "precio_unitario_max": 55000},
    "L": {"ingresos_brutos_anual": 21600000, "alquileres_anual": 1512000, "precio_unitario_max": 55000},
    "M": {"ingresos_brutos_anual": 23400000, "alquileres_anual": 1638000, "precio_unitario_max": 55000},
    "N": {"ingresos_brutos_anual": 25200000, "alquileres_anual": 1764000, "precio_unitario_max": 55000}
}'::jsonb, 'Categorías de Monotributo 2026 con topes de ingresos y precio unitario máximo', '2026-01-01'),

('monotributo_cuotas_2026', '{
    "A": 13500, "B": 19000, "C": 24500, "D": 30000,
    "E": 35500, "F": 41000, "G": 46500, "H": 52000,
    "I": 57500, "J": 63000, "K": 68500, "L": 74000,
    "M": 79500, "N": 85000
}'::jsonb, 'Valores mensuales de cuotas de Monotributo 2026', '2026-01-01'),

('iva_alicuotas', '{
    "general": 21,
    "reducida": 10.5,
    "aumentada": 27,
    "exento": 0
}'::jsonb, 'Alícuotas de IVA vigentes', '2026-01-01'),

('ganancias_alicuotas', '{
    "cuarta_categoria": 35,
    "segunda_categoria": 35
}'::jsonb, 'Alícuotas de Ganancias', '2026-01-01');

-- ============================================
-- TENANT Y USUARIO DEMO (SOLO DESARROLLO)
-- ============================================
-- En producción, estos se crean manualmente

INSERT INTO tenants (nombre, cuit, email)
VALUES ('Estudio Demo', '20123456789', 'demo@estudio.com');

-- Password: admin123 (hash bcrypt)
INSERT INTO usuarios (tenant_id, email, password_hash, nombre, rol)
VALUES (
    1,
    'admin@estudio.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu',
    'Administrador',
    'admin_estudio'
);
