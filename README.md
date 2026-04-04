# AccountantOS v9.7 — Sistema Contable para Argentina

**Automatización completa para contadores independientes**

Descarga comprobantes de ARCA, procesa facturas con OCR, calcula Monotributo,
genera VEPs y crea paquetes para el banco — todo automático.

---

## Para Marcos — Instalación (una sola vez)

```powershell
# 1. Clonar el repo
cd Desktop
git clone https://github.com/SOCRAMbt/AccountOS.git
cd AccountOS

# 2. Levantar con Docker
cd docker
docker compose up -d

# 3. Esperar a que los 9 servicios digan "healthy" (~2 min)
docker compose ps

# 4. Seed parámetros fiscales
cd ..\backend
docker exec -i accountantos-backend python -m app.utils.seed_parametros_fiscales

# 5. Setup persona física
docker exec -i accountantos-backend python -m app.utils.setup_persona_fisica ^
  20TU-CUIT "Tu Nombre" tu@email.com TuPassword123

# 6. Abrir en navegador
start http://localhost:3000
```

## Para la Contadora — Primer Uso

1. Abrí **http://localhost:3000** en tu navegador
2. Entrá con tu email y contraseña
3. Andá a **Configuración** (menú lateral):
   - Subí tu certificado `.cer` de ARCA
   - Subí tu clave privada `.key`
   - Poné tu CUIT y nombre
   - Elegí "Prueba" para empezar
4. Andá a **Clientes** → **Nuevo cliente** y cargá el primer CUIT
5. Hacé click en **"Verificar delegación ARCA"**
6. Volvé al **Dashboard** y tocá **"Sincronizar ARCA"**

## Uso Diario

| Qué hacés | Dónde |
|-----------|-------|
| Ver qué clientes necesitan atención | **Dashboard** (semáforo rojo/amarillo/verde) |
| Sincronizar facturas de ARCA | **Dashboard** → botón "Sincronizar ARCA" |
| Revisar facturas pendientes | **Comprobantes** → pestaña "Delta" |
| Subir una foto de factura | **Cargar Factura** (cámara o archivo) |
| Aprobar VEPs de Monotributo | **VEPs** → botón "Aprobar" |
| Generar paquete para el banco | **Bank-Kit** → seleccionar cliente y mes |
| Ver alertas urgentes | **Alertas** (tiene badge rojo si hay nuevas) |

## Cuando el Banco Pide Algo

1. Menú → **Bank-Kit**
2. Elegí el cliente y el mes
3. Hacé click en **"Generar paquete"**
4. Se descarga un ZIP con:
   - Libro IVA Ventas (PDF)
   - Libro IVA Compras (PDF)
   - Constancia de Inscripción (PDF)

## Tecnologías

- **Backend:** Python 3.12 + FastAPI + PostgreSQL 16
- **Frontend:** Next.js 14 + React Query + Tailwind CSS
- **Workers:** Celery + Redis (tareas automáticas)
- **ARCA/AFIP:** WSAA (PKCS7/CMS), WSFE, WSCDC, Padrones
- **OCR:** Google Vertex AI (Gemini 1.5 Pro) — opcional

## Estado del Proyecto

- ✅ 29 endpoints API funcionales
- ✅ 12 modelos de base de datos con migraciones
- ✅ 8 páginas frontend completas
- ✅ 5 hooks React Query
- ✅ RLS (Row-Level Security) activado
- ✅ Firma PKCS7/CMS real para WSAA
- ✅ Delta-Processing con 7 estados
- ✅ Motor Fiscal Monotributo con triggers
- ✅ Bank-Kit con PDFs reales (reportlab)
- ✅ Ingesta de fotos con OCR
- ✅ 12 tareas Celery programadas

**Completitud estimada: ~95%**
(el 5% restante es configuración externa: Google Cloud y certificado ARCA real)

---

Para soporte técnico, contactar a Marcos.
