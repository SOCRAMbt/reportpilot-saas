# AccountantOS — Arranque Rápido (10 pasos)

Para Marcos — ejecutar en orden, una vez sola.

```
□ 1. cd C:\Users\Marcos\Desktop\AccountantOS\docker
   docker compose up -d

□ 2. Esperar que diga "healthy" en los 9 servicios
   docker compose ps
   (debería decir "healthy" en postgres y redis, "Up" en los demás)

□ 3. Seed parámetros fiscales
   cd ..\backend
   docker exec -i accountantos-backend python -m app.utils.seed_parametros_fiscales

□ 4. Setup persona física
   docker exec -i accountantos-backend python -m app.utils.setup_persona_fisica ^
     20123456789 "María García" maria@miestudio.com MiPassword123

□ 5. Abrir http://localhost:3000 en el navegador

□ 6. Login con maria@miestudio.com / MiPassword123

□ 7. Ir a Configuración → subir .cer y .key de ARCA
   (si no tenés certificado, pedilo en arca.gob.ar)

□ 8. Ir a Clientes → Nuevo cliente → cargar CUIT y nombre

□ 9. Ir a Clientes → clic en "Verificar delegación ARCA"
   (si falla, el cliente debe delegar en arca.gob.ar primero)

□ 10. Dashboard → botón "Sincronizar ARCA"
    (descarga facturas del mes de todos los clientes)
```

## URLs después del arranque

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8001/docs |
| Health | http://localhost:8001/health |
| Flower (Celery) | http://localhost:5555 |

## Si algo falla

```powershell
# Ver logs del backend
docker logs accountantos-backend

# Ver logs del frontend
docker logs accountantos-frontend

# Reiniciar todo
cd docker
docker compose down
docker compose up -d
```
