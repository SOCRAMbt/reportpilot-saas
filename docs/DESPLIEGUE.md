# Guía de Despliegue - AccountantOS v9.7

## Checklist Pre-Despliegue

### 1. Configuración de ARCA/AFIP

- [ ] Obtener certificado digital (.cer) de AFIP
- [ ] Obtener clave privada (.key)
- [ ] Obtener CA de AFIP
- [ ] Configurar Administrador de Relaciones
- [ ] Verificar CUIT del estudio
- [ ] Probar conexión en homologación

### 2. Variables de Entorno

```bash
# Copiar y editar
cp backend/.env.example backend/.env.prod
```

**Valores críticos a verificar:**

| Variable | Verificación |
|----------|--------------|
| `SECRET_KEY` | Mínimo 32 caracteres, único |
| `JWT_SECRET_KEY` | Mínimo 32 caracteres, único |
| `ARCA_CERT_PATH` | Ruta absoluta al certificado |
| `ARCA_KEY_PATH` | Ruta absoluta a la clave |
| `ARCA_AMBIENTE` | `pro` para producción |
| `DATABASE_PASSWORD` | Contraseña segura |
| `HMAC_SALT_MASTER` | Mínimo 32 caracteres |

### 3. KMS Bootstrap

**NUNCA usar variables de entorno para credenciales KMS.**

Configurar según proveedor:

**AWS (IMDSv2):**
```bash
# El sistema obtiene credenciales automáticamente desde EC2
# No configurar AWS_ACCESS_KEY_ID
```

**GCP (Instance Identity):**
```bash
# El sistema obtiene credenciales desde metadata server
```

**HashiCorp Vault:**
```bash
export VAULT_URL=https://vault.tuempresa.com
# VAULT_ROLE_ID y VAULT_SECRET_ID se inyectan en runtime
```

### 4. Redis sin Persistencia

Verificar configuración en `docker-compose.yml`:

```yaml
redis:
  command: redis-server --appendonly no --save ""
```

**CRÍTICO:** Los tokens WSAA NO deben persistir en disco.

### 5. AAIP Inscripción

- [ ] Inscripción como banco de datos personales
- [ ] Política de privacidad publicada
- [ ] Contratos de confidencialidad firmados

---

## Despliegue en Producción

### Paso 1: Subir código al servidor

```bash
scp -r accountantos/ user@servidor:/opt/accountantos
```

### Paso 2: Configurar Docker Compose

```bash
cd /opt/accountantos/docker

# Copiar configuración de producción
cp docker-compose.yml docker-compose.prod.yml

# Editar variables de entorno
nano .env.production
```

### Paso 3: Iniciar servicios

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Paso 4: Verificar logs

```bash
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### Paso 5: Ejecutar health check

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "api": "ok",
  "version": "9.7.0",
  "database": "ok",
  "redis": "ok"
}
```

---

## Configuración de Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name accountantos.tuempresa.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name accountantos.tuempresa.com;

    ssl_certificate /etc/letsencrypt/live/accountantos.tuempresa.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/accountantos.tuempresa.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Monitoreo

### Prometheus Metrics

Acceder a: `http://localhost:9090/metrics`

### Celery Flower

Acceder a: `http://localhost:5555`

### Logs

```bash
# Ver logs en tiempo real
docker-compose logs -f backend

# Ver logs de un servicio específico
docker-compose logs -f celery-worker

# Buscar errores
docker-compose logs backend | grep ERROR
```

---

## Backup de Base de Datos

### Script de Backup

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/accountantos

docker exec accountantos-db pg_dump \
    -U accountantos \
    -d accountantos \
    > ${BACKUP_DIR}/backup_${DATE}.sql

# Comprimir
gzip ${BACKUP_DIR}/backup_${DATE}.sql

# Mantener últimos 7 días
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
```

### Restaurar Backup

```bash
gunzip backup_20260328_120000.sql.gz

docker exec -i accountantos-db psql \
    -U accountantos \
    -d accountantos \
    < backup_20260328_120000.sql
```

---

## Troubleshooting

### Error: "El CEE ya posee un TA válido"

**Causa:** Clock skew entre servidor y AFIP

**Solución:**
```bash
# Sincronizar reloj
sudo ntpdate time.afip.gov.ar

# O usar systemd-timesyncd
sudo timedatectl set-ntp true
```

### Error: Rate limit excedido

**Causa:** Más de 50 requests/minuto a ARCA

**Solución:**
- Verificar logs de rate limiting
- Ajustar `RATE_LIMIT_PER_MINUTE` en .env
- Verificar que Token Bucket está funcionando

### Error: Token WSAA expirado

**Causa:** TTL mal configurado

**Solución:**
- Verificar que Redis no tiene persistencia
- Verificar TTL en `wsaa.py` (TOKEN_TTL_PRODUCCION = 120)

---

## Contacto de Emergencia

Para incidentes de producción, contactar:

- Email: soporte@tuempresa.com
- Teléfono: +54 11 XXXX-XXXX
