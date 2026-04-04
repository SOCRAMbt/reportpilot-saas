"""
Setup inicial para modo persona física.
Crea el tenant único y el usuario administrador si no existen.
Llamar una sola vez al iniciar el sistema por primera vez.

Uso: python -m app.utils.setup_persona_fisica CUIT NOMBRE EMAIL PASSWORD
"""
import asyncio
import sys
from app.db import AsyncSessionLocal
from app.models import Tenant, Usuario
from app.core.security import hash_password
from sqlalchemy import select


async def setup_inicial(
    cuit_contadora: str,
    nombre: str,
    email: str,
    password: str,
):
    async with AsyncSessionLocal() as session:
        resultado = await session.execute(select(Tenant).where(Tenant.id == 1))
        tenant = resultado.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                id=1,
                nombre=nombre,
                cuit=cuit_contadora,
                email=email,
                activo=True,
                plan="personal",
                configuracion={
                    "modo": "persona_fisica",
                    "cuit_operador": cuit_contadora,
                    "arca_ambiente": "hom",
                }
            )
            session.add(tenant)

        res_u = await session.execute(
            select(Usuario).where(Usuario.tenant_id == 1, Usuario.rol == "admin_estudio")
        )
        if not res_u.scalar_one_or_none():
            usuario = Usuario(
                tenant_id=1,
                email=email,
                password_hash=hash_password(password),
                nombre=nombre,
                rol="admin_estudio",
                activo=True,
            )
            session.add(usuario)

        await session.commit()
        print(f"✅ Setup completado para {nombre} (CUIT: {cuit_contadora[:4]}*****)")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Uso: python -m app.utils.setup_persona_fisica CUIT NOMBRE EMAIL PASSWORD")
        sys.exit(1)
    asyncio.run(setup_inicial(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
