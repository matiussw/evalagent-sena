"""Infraestructura de tests.

Se usa SQLite en memoria para que la suite corra sin Postgres. Los tipos
específicos de Postgres (JSONB, UUID) se compilan a equivalentes de SQLite
mediante `@compiles`, y el índice parcial se omite: SQLite no lo soporta y la
regla que impone (RI-7) ya está verificada por `test_modelos.py` sobre los
metadatos.

Los tests que dependen de comportamiento exclusivo de Postgres se marcan con
`@pytest.mark.postgres` y solo corren en CI, donde sí hay servidor.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateIndex

from app.core.security import hashear_password
from app.db.session import get_sesion
from app.main import app
from app.models import Base, Ficha, Institucion, RolUsuario, Usuario


# --- Compatibilidad de tipos Postgres -> SQLite ---------------------------- #
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(type_, compiler, **kw):  # noqa: ANN001, ARG001
    return "JSON"


@compiles(PgUUID, "sqlite")
def _uuid_sqlite(type_, compiler, **kw):  # noqa: ANN001, ARG001
    return "CHAR(36)"


@compiles(CreateIndex, "sqlite")
def _indice_sqlite(create, compiler, **kw):  # noqa: ANN001
    # SQLite no admite el índice parcial con la sintaxis de Postgres.
    if create.element.name == "idx_sesion_unica_por_guia":
        return "SELECT 1"
    return compiler.visit_create_index(create, **kw)


@pytest_asyncio.fixture
async def motor():
    motor = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with motor.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    yield motor
    await motor.dispose()


@pytest_asyncio.fixture
async def bd(motor) -> AsyncGenerator[AsyncSession, None]:
    fabrica = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with fabrica() as sesion:
        yield sesion


@pytest_asyncio.fixture
async def cliente(bd: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _sesion_de_prueba():
        yield bd

    app.dependency_overrides[get_sesion] = _sesion_de_prueba
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test/api/v1") as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Datos de prueba
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture
async def institucion_a(bd: AsyncSession) -> Institucion:
    inst = Institucion(nombre="Centro de Servicios y Gestión Empresarial", nit="800111222")
    bd.add(inst)
    await bd.commit()
    return inst


@pytest_asyncio.fixture
async def institucion_b(bd: AsyncSession) -> Institucion:
    inst = Institucion(nombre="Centro de Diseño Tecnológico Industrial", nit="800333444")
    bd.add(inst)
    await bd.commit()
    return inst


async def _crear_usuario(
    bd: AsyncSession, institucion: Institucion, rol: RolUsuario, email: str
) -> Usuario:
    usuario = Usuario(
        nombre=email.split("@")[0].title(),
        email=email,
        password_hash=hashear_password("claveDePrueba2026"),
        rol=rol,
        institucion_id=institucion.id,
    )
    bd.add(usuario)
    await bd.commit()
    return usuario


@pytest_asyncio.fixture
async def docente_a(bd, institucion_a) -> Usuario:
    return await _crear_usuario(
        bd, institucion_a, RolUsuario.DOCENTE, "carolina@sena.edu.co"
    )


@pytest_asyncio.fixture
async def docente_b(bd, institucion_b) -> Usuario:
    return await _crear_usuario(
        bd, institucion_b, RolUsuario.DOCENTE, "otro.docente@sena.edu.co"
    )


@pytest_asyncio.fixture
async def aprendiz_a(bd, institucion_a) -> Usuario:
    return await _crear_usuario(
        bd, institucion_a, RolUsuario.APRENDIZ, "jhon@aprendiz.sena.edu.co"
    )


@pytest_asyncio.fixture
async def aprendiz_b(bd, institucion_b) -> Usuario:
    return await _crear_usuario(
        bd, institucion_b, RolUsuario.APRENDIZ, "otra.aprendiz@sena.edu.co"
    )


@pytest.fixture
def token_de():
    """Genera el encabezado Authorization de un usuario."""
    from app.core.security import crear_token_acceso

    def _token(usuario: Usuario) -> dict[str, str]:
        acceso = crear_token_acceso(
            usuario_id=usuario.id,
            rol=usuario.rol.value,
            institucion_id=usuario.institucion_id,
        )
        return {"Authorization": f"Bearer {acceso}"}

    return _token


@pytest_asyncio.fixture
async def ficha_a(bd, institucion_a, docente_a) -> Ficha:
    ficha = Ficha(
        institucion_id=institucion_a.id,
        docente_id=docente_a.id,
        codigo="2758421",
        nombre="Análisis y Desarrollo de Software",
        programa="ADSO",
        trimestre="2026-2",
    )
    bd.add(ficha)
    await bd.commit()
    return ficha


@pytest.fixture
def rubrica_valida() -> dict:
    return {
        "umbral_aprobacion": 60,
        "criterios": [
            {"nombre": "Endpoints", "descripcion": "Verbos HTTP y rutas", "peso": 25},
            {"nombre": "Manejo de errores", "descripcion": "Códigos de estado", "peso": 20},
            {"nombre": "Diseño", "descripcion": "Decisiones de arquitectura", "peso": 20},
            {"nombre": "Seguridad", "descripcion": "Autenticación", "peso": 15},
            {"nombre": "Explicación", "descripcion": "Claridad al explicar", "peso": 20},
        ],
    }


@pytest.fixture
def id_inexistente() -> uuid.UUID:
    return uuid.uuid4()
