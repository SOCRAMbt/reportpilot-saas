# AccountantOS v9.7

**Sistema de Automatización Contable Integral para Argentina**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 📋 Índice

- [Descripción](#descripción)
- [Características Principales](#características-principales)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Despliegue](#despliegue)
- [API Documentation](#api-documentation)

---

## Descripción

AccountantOS es un sistema de automatización contable diseñado para estudios contables en Argentina. Se conecta directamente con los servicios web de ARCA (AFIP) para:

- Descargar comprobantes emitidos automáticamente
- Validar existencia de comprobantes recibidos
- Pre-liquidar obligaciones fiscales (VEPs)
- Monitorear riesgo fiscal de clientes (Monotributo)
- Procesar facturas físicas con OCR + IA

### Principios de Diseño

1. **Verdad Digital Preexistente**: El sistema consume datos ya disponibles en ARCA
2. **Delta-Processing**: Solo se procesan novedades, no duplicados
3. **Aprobación Humana**: El contador es el aprobador indelegable de actos fiscales
4. **Degradación Elegante**: Funciona incluso cuando ARCA no responde

---

## Características Principales

### 🔗 Conexión ARCA/AFIP

| Servicio | Estado | Descripción |
|----------|--------|-------------|
| WSAA | ✅ | Autenticación con certificados |
| WSFE | ✅ | Facturación electrónica |
| WSCDC | ✅ | Descarga masiva de comprobantes |
| WSFEX | ✅ | Exportaciones |
| Padrones | ✅ | Validación de CUITs |
| Constancia Inscripción | ✅ | Verificación de categoría |

### 🧠 Delta-Processing v9.7

- 7 estados de comprobante según ARCA
- Comparación de 6 campos críticos (no binaria)
- Lock distribuido en Redis para prevenir race conditions
- Re-verificación automática T+7 y T+30 días

### 📷 OCR con IA

- Gemini 1.5 Pro vía Vertex AI (Enterprise con ZDR)
- System prompt blindado contra prompt injection
- HMAC-SHA256 para tokenización de CUITs
- Confidence score por campo crítico

### 📊 Motor de Riesgo Fiscal

- Cálculo de categorías de Monotributo
- Anualización proporcional (< 12 meses de actividad)
- Alertas en ventanas enero/julio ±30 días
- Trigger por tope anual absoluto
- Trigger por precio unitario máximo (facturas C)

### 💳 Flujo de VEPs

- Pre-liquidación automática (días 13, 21, 23)
- Portal del cliente con 2FA TOTP
- Friction cognitiva para montos altos
- Verificación de pago a 24hs

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
│                    http://localhost:3000                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                     │
│                    http://localhost:8000                     │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Redis       │  │   Celery        │
│   (Datos)       │  │   (Caché)       │  │   (Workers)     │
│   :5432         │  │   :6379         │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICIOS EXTERNOS                        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│   │ ARCA/AFIP│  │  Gemini  │  │  KMS     │                 │
│   │   WS     │  │   OCR    │  │  Claves  │                 │
│   └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Requisitos

### Desarrollo

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose
- Git

### Producción

- Servidor Linux (Ubuntu 22.04+)
- 4 CPU cores mínimo
- 8 GB RAM mínimo
- 50 GB SSD
- Certificado SSL

### ARCA/AFIP

- Certificado digital (.pem)
- Clave fiscal nivel 3
- Administrador de Relaciones configurado
- CUIT del estudio

---

## Instalación

### 1. Clonar repositorio

```bash
git clone https://github.com/tu-usuario/accountantos.git
cd accountantos
```

### 2. Configurar variables de entorno

```bash
cd backend
cp .env.example .env
# Editar .env con tus valores
```

### 3. Levantar servicios con Docker

```bash
cd docker
docker-compose up -d
```

### 4. Ejecutar migraciones

```bash
cd ../backend
alembic upgrade head
```

### 5. Iniciar desarrollo

```bash
# Backend (terminal 1)
cd backend
uvicorn app.main:app --reload

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Acceder a:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Flower (Celery): http://localhost:5555

---

## Configuración

### Variables de Entorno Principales

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de PostgreSQL | `postgresql://user:pass@localhost:5432/accountantos` |
| `REDIS_URL` | URL de Redis | `redis://localhost:6379/0` |
| `ARCA_CERT_PATH` | Ruta al certificado | `/app/certs/certificado.cer` |
| `ARCA_KEY_PATH` | Ruta a la clave | `/app/certs/clave.key` |
| `ARCA_CUIT_ESTUDIO` | CUIT del estudio | `20123456789` |
| `ARCA_AMBIENTE` | Ambiente (hom/pro) | `hom` |
| `SECRET_KEY` | Clave secreta | `minclave_muy_larga` |

### Configuración de ARCA

1. Obtener certificado digital en AFIP
2. Configurar Administrador de Relaciones
3. Los clientes deben delegar acceso al CUIT del estudio

Ver [docs/CONFIGURACION_ARCA.md](docs/CONFIGURACION_ARCA.md) para instrucciones detalladas.

---

## Despliegue

### Producción con Docker

```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

### Checklist Pre-Despliegue

- [ ] Certificados ARCA instalados
- [ ] Variables de entorno configuradas
- [ ] KMS bootstrap con Instance Identity
- [ ] Redis sin persistencia (appendonly no)
- [ ] AAIP inscripción aprobada
- [ ] HTTPS configurado
- [ ] Backups automáticos

---

## API Documentation

La API sigue REST conventions. Ver documentación interactiva:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Iniciar sesión |
| GET | `/api/v1/comprobantes` | Listar comprobantes |
| POST | `/api/v1/comprobantes` | Crear comprobante |
| POST | `/api/v1/comprobantes/ocr` | Procesar OCR |
| GET | `/api/v1/veps` | Listar VEPs |
| POST | `/api/v1/veps/pre-liquidar` | Pre-liquidar VEP |

---

## Tests

```bash
# Backend
cd backend
pytest --cov=app

# Frontend
cd frontend
npm test
```

---

## Seguridad

### Características

- HMAC-SHA256 para tokenización de CUITs
- JWT con expiración corta (30 min)
- Row-Level Security en PostgreSQL
- Redis sin persistencia para tokens WSAA
- System prompt blindado en OCR

### Plan de Respuesta a Incidentes

Ver [docs/SEGURIDAD.md](docs/SEGURIDAD.md) para el plan completo.

---

## Licencia

Proprietary - Uso interno del estudio

---

## Contacto

Para soporte técnico, contactar al equipo de desarrollo.
