"""Repositorio base con filtro de tenant obligatorio (T-004 · ADR-003).

Regla de oro del aislamiento multi-tenant: **el identificador de institución se
deriva del token JWT, nunca de un parámetro que envíe el cliente**.

Todo acceso a datos de dominio pasa por aquí. Un servicio que construya una
consulta por su cuenta, saltándose esta clase, abre una fuga entre
instituciones — por eso el test parametrizado sobre todos los endpoints es
obligatorio en CI.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import ModeloBase

M = TypeVar("M", bound=ModeloBase)


class RepositorioTenant(Generic[M]):
    """Acceso a datos acotado a una institución.

    Las subclases indican en `columna_tenant` cómo se alcanza la institución
    desde su modelo. Para entidades que la llevan directamente es
    `institucion_id`; para las que cuelgan de otra (guías, sesiones) se
    sobreescribe `_filtro_tenant`.
    """

    modelo: type[M]
    columna_tenant: str = "institucion_id"

    def __init__(self, sesion: AsyncSession, institucion_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._institucion_id = institucion_id

    # ---------------------------------------------------------------- filtro
    def _filtro_tenant(self, consulta: Select) -> Select:
        columna = getattr(self.modelo, self.columna_tenant)
        return consulta.where(columna == self._institucion_id)

    def _base(self) -> Select:
        return self._filtro_tenant(select(self.modelo))

    # ------------------------------------------------------------- lecturas
    async def obtener(self, id_: uuid.UUID) -> M | None:
        """Devuelve la entidad, o None si no existe **o es de otro tenant**.

        La capa de API traduce el None a un 404. Devolver 404 y no 403 evita
        confirmar la existencia de recursos ajenos.
        """
        resultado = await self._sesion.execute(self._base().where(self.modelo.id == id_))
        return resultado.scalar_one_or_none()

    async def listar(self, *, offset: int = 0, limite: int = 20, **filtros: Any) -> list[M]:
        consulta = self._base()
        for campo, valor in filtros.items():
            if valor is not None:
                consulta = consulta.where(getattr(self.modelo, campo) == valor)
        consulta = consulta.offset(offset).limit(limite).order_by(self.modelo.creado_en.desc())
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())

    async def contar(self, **filtros: Any) -> int:
        consulta = self._filtro_tenant(select(func.count()).select_from(self.modelo))
        for campo, valor in filtros.items():
            if valor is not None:
                consulta = consulta.where(getattr(self.modelo, campo) == valor)
        resultado = await self._sesion.execute(consulta)
        return int(resultado.scalar_one())

    # ---------------------------------------------------------- escrituras
    async def crear(self, entidad: M) -> M:
        """Fija el tenant desde el token, ignorando lo que trajera la entidad."""
        if hasattr(entidad, self.columna_tenant):
            setattr(entidad, self.columna_tenant, self._institucion_id)
        self._sesion.add(entidad)
        await self._sesion.flush()
        return entidad

    async def eliminar(self, entidad: M) -> None:
        await self._sesion.delete(entidad)
        await self._sesion.flush()
