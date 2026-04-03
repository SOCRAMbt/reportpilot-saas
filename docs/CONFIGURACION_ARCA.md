# Configuración de ARCA/AFIP - Guía Paso a Paso

## Requisitos Previos

1. **Clave Fiscal Nivel 3**
   - Obtener en cualquier oficina de AFIP
   - Llevar DNI y CUIT
   - Nivel 3 requerido para operaciones web service

2. **Certificado Digital**
   - Válido por 12 meses
   - Formato .pem recomendado

---

## Paso 1: Obtener Certificado Digital

### Opción A: Desde AFIP (Recomendado)

1. Ingresar a [AFIP](https://www.afip.gob.ar)
2. Ir a **Certificado Digital** → **Generar Certificado**
3. Seleccionar **Persona Humana** o **Persona Jurídica**
4. Descargar en formato `.pem`

### Opción B: OpenSSL (Alternativo)

```bash
# Generar clave privada
openssl genrsa -out clave.key 2048

# Generar CSR (Certificate Signing Request)
openssl req -new -key clave.key -out certificado.csr

# Enviar CSR a AFIP y descargar certificado
```

### Archivos Necesarios

| Archivo | Descripción | Ejemplo |
|---------|-------------|---------|
| `certificado.cer` | Certificado público | `-----BEGIN CERTIFICATE-----` |
| `clave.key` | Clave privada | `-----BEGIN PRIVATE KEY-----` |
| `ca_afip.crt` | CA de AFIP | Proporcionado por AFIP |

---

## Paso 2: Configurar Administrador de Relaciones

El **Administrador de Relaciones** permite que los clientes deleguen acceso al estudio.

### 2.1. Dar de Alta el Servicio

1. Ingresar a **Administrador de Relaciones**
2. Ir a **Servicios** → **Agregar Servicio**
3. Buscar **Servicios Web - Facturación Electrónica**
4. Aceptar términos y condiciones

### 2.2. Configurar Relaciones

1. Ir a **Relaciones** → **Nueva Relación**
2. Seleccionar **Tipo de relación**: "Mi cliente"
3. Ingresar CUIT del cliente
4. Seleccionar servicios a los que tendrá acceso:
   - Facturación Electrónica
   - Consulta de Padrones
   - Constancia de Inscripción
5. Confirmar con Clave Fiscal

### 2.3. Instrucciones para Clientes

Los clientes deben:

1. Ingresar a su cuenta de AFIP
2. Ir a **Administrador de Relaciones**
3. **Dar una relación** → **A un servicio**
4. Buscar el CUIT del estudio
5. Seleccionar los servicios
6. Confirmar

---

## Paso 3: Configurar WSAA

WSAA (Web Services Authentication & Authorization) es el servicio de autenticación.

### 3.1. Generar TRA (Ticket de Request de Acceso)

El sistema genera automáticamente el TRA. Ver `backend/app/services/wsaa.py`.

### 3.2. Obtener TA (Ticket de Acceso)

El sistema solicita el TA a WSAA y lo cachea en Redis.

### 3.3. URLs por Ambiente

| Ambiente | URL WSAA |
|----------|----------|
| Homologación | `https://wsaahomo.afip.gov.ar/ws/services/LoginCms` |
| Producción | `https://wsaa.afip.gov.ar/ws/services/LoginCms` |

---

## Paso 4: Probar Conexión

### Script de Test

```python
# test_arca.py
from app.services.wsaa import obtener_ta, sync_ntp_afip

# Sincronizar reloj
sync_ntp_afip()

# Obtener token para WSFE
token, signature = await obtener_ta("wsfe")

print(f"Token: {token[:50]}...")
print(f"Signature: {signature[:50]}...")
```

### Verificar en Logs

```bash
docker-compose logs backend | grep "TA obtenido"
```

Debe mostrar:
```
INFO: TA obtenido para servicio wsfe
```

---

## Paso 5: Servicios Disponibles

### Servicios de Facturación

| Servicio | Código | Descripción |
|----------|--------|-------------|
| WSFE | `wsfe` | Comprobantes clase A, B, C |
| WSFEX | `wsfex` | Exportaciones |
| WSBFE | `wsbfe` | Bonos fiscales |
| WSCT | `wsct` | Servicios turísticos |
| WSMTXCA | `wsmtxca` | Detalle de ítems |

### Servicios de Consulta

| Servicio | Código | Descripción |
|----------|--------|-------------|
| WSCDC | `wscdc` | Descarga masiva |
| Padrón A4 | `padron_a4` | Contribuyentes |
| Padrón A5 | `padron_a5` | Contribuyentes ampliado |
| Constancia | `constancia_inscripcion` | Categoría fiscal |

---

## Paso 6: Rate Limiting

ARCA tiene límite de **~50 requests/minuto** por CUIT.

### Configuración Recomendada

```env
# Backend .env
RATE_LIMIT_PER_MINUTE=50
```

### Circuit Breaker

El sistema implementa Circuit Breaker que:

- **429 (Rate Limit)**: Aplica backoff, NO abre circuito
- **5xx (Error)**: Abre circuito después de 5 fallos
- **Timeout**: Abre circuito después de 5 fallos

---

## Troubleshooting

### Error: "Falla de conexión"

**Causas posibles:**
- Certificado expirado
- Clave incorrecta
- Firewall bloqueando conexión

**Solución:**
```bash
# Verificar validez del certificado
openssl x509 -in certificado.cer -text -noout | grep "Not After"

# Verificar que la clave coincide
openssl x509 -noout -modulus -in certificado.cer | openssl md5
openssl rsa -noout -modulus -in clave.key | openssl md5
# Deben dar el mismo hash
```

### Error: "Relación no encontrada"

**Causa:** El cliente no delegó acceso

**Solución:**
1. Contactar al cliente
2. Enviar instrucciones del Paso 2.3
3. Verificar en Administrador de Relaciones

### Error: "Token expirado"

**Causa:** TTL mal configurado o Redis con persistencia

**Solución:**
```bash
# Verificar configuración de Redis
docker exec accountantos-redis redis-cli CONFIG GET appendonly
# Debe ser "no"

docker exec accountantos-redis redis-cli CONFIG GET save
# Debe ser ""
```

---

## Contacto

Para soporte con ARCA/AFIP:

- **AFIP - Mesa de Ayuda:** 0810-666-4455
- **Email:** serviciosweb@afip.gob.ar
