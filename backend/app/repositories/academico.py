"""Repositorios del dominio académico.

Guías y sesiones no llevan `institucion_id` propio: cuelgan de una ficha, que sí
lo lleva. Por eso sobreescriben `_filtro_tenant` con un JOIN — el aislamiento se
mantiene aunque la columna no esté en la tabla.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.models.academico import Ficha, Guia, Inscripcion, Rubrica
from app.models.enums import EstadoGuia, EstadoInscripcion
from app.models.identidad import Usuario
from app.models.sustentacion import Sesion
from app.repositories.base import RepositorioTenant


class RepositorioUsuarios(RepositorioTenant[Usuario]):
    modelo = Usuario

    async def por_email(self, email: str) -> Usuario | None:
        """Búsqueda global, sin filtro de tenant.

        El email es único a nivel de sistema: hay que poder detectar el
        duplicado aunque la cuenta existente sea de otra institución. Es la
        única lectura de usuario que se salta el filtro, y no expone la entidad
        fuera del servicio de autenticación.
        """
        resultado = await self._sesion.execute(
            select(Usuario).where(Usuario.email == email.lower())
        )
        return resultado.scalar_one_or_none()


class RepositorioFichas(RepositorioTenant[Ficha]):
    modelo = Ficha

    async def por_codigo(self, codigo: str) -> Ficha | None:
        resultado = await self._sesion.execute(
            self._base().where(Ficha.codigo == codigo)
        )
        return resultado.scalar_one_or_none()

    async def de_docente(self, docente_id: uuid.UUID, **kwargs) -> list[Ficha]:
        return await self.listar(docente_id=docente_id, **kwargs)

    async def donde_esta_inscrito(self, aprendiz_id: uuid.UUID) -> list[Ficha]:
        consulta = (
            self._base()
            .join(Inscripcion, Inscripcion.ficha_id == Ficha.id)
            .where(
                Inscripcion.aprendiz_id == aprendiz_id,
                Inscripcion.estado == EstadoInscripcion.ACTIVA,
            )
        )
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())


class RepositorioInscripciones(RepositorioTenant[Inscripcion]):
    modelo = Inscripcion

    def _filtro_tenant(self, consulta: Select) -> Select:
        return consulta.join(Ficha, Ficha.id == Inscripcion.ficha_id).where(
            Ficha.institucion_id == self._institucion_id
        )

    async def crear(self, entidad: Inscripcion) -> Inscripcion:
        # No tiene columna de tenant propia: lo hereda de la ficha.
        self._sesion.add(entidad)
        await self._sesion.flush()
        return entidad

    async def activa(
        self, *, ficha_id: uuid.UUID, aprendiz_id: uuid.UUID
    ) -> Inscripcion | None:
        resultado = await self._sesion.execute(
            self._base().where(
                Inscripcion.ficha_id == ficha_id,
                Inscripcion.aprendiz_id == aprendiz_id,
                Inscripcion.estado == EstadoInscripcion.ACTIVA,
            )
        )
        return resultado.scalar_one_or_none()


class RepositorioGuias(RepositorioTenant[Guia]):
    modelo = Guia

    def _filtro_tenant(self, consulta: Select) -> Select:
        return consulta.join(Ficha, Ficha.id == Guia.ficha_id).where(
            Ficha.institucion_id == self._institucion_id
        )

    async def crear(self, entidad: Guia) -> Guia:
        self._sesion.add(entidad)
        await self._sesion.flush()
        return entidad

    async def con_rubrica(self, guia_id: uuid.UUID) -> Guia | None:
        consulta = (
            self._base()
            .where(Guia.id == guia_id)
            .options(selectinload(Guia.rubrica).selectinload(Rubrica.criterios))
        )
        resultado = await self._sesion.execute(consulta)
        return resultado.scalar_one_or_none()

    async def publicadas_para_aprendiz(self, aprendiz_id: uuid.UUID) -> list[Guia]:
        """Solo guías publicadas de fichas donde el aprendiz está inscrito."""
        consulta = (
            self._base()
            .join(Inscripcion, Inscripcion.ficha_id == Guia.ficha_id)
            .where(
                Inscripcion.aprendiz_id == aprendiz_id,
                Inscripcion.estado == EstadoInscripcion.ACTIVA,
                Guia.estado == EstadoGuia.PUBLICADA,
            )
        )
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())


class RepositorioSesiones(RepositorioTenant[Sesion]):
    modelo = Sesion

    def _filtro_tenant(self, consulta: Select) -> Select:
        return (
            consulta.join(Guia, Guia.id == Sesion.guia_id)
            .join(Ficha, Ficha.id == Guia.ficha_id)
            .where(Ficha.institucion_id == self._institucion_id)
        )

    async def crear(self, entidad: Sesion) -> Sesion:
        self._sesion.add(entidad)
        await self._sesion.flush()
        return entidad

    async def con_turnos(self, sesion_id: uuid.UUID) -> Sesion | None:
        consulta = (
            self._base()
            .where(Sesion.id == sesion_id)
            .options(
                selectinload(Sesion.turnos),
                selectinload(Sesion.guia),
                selectinload(Sesion.aprendiz),
                selectinload(Sesion.revision),
            )
        )
        resultado = await self._sesion.execute(consulta)
        return resultado.scalar_one_or_none()

    async def activa_de_aprendiz(
        self, *, guia_id: uuid.UUID, aprendiz_id: uuid.UUID
    ) -> Sesion | None:
        """Sesión no abandonada del aprendiz para esa guía (regla RI-7)."""
        from app.models.enums import EstadoSesion

        resultado = await self._sesion.execute(
            self._base().where(
                Sesion.guia_id == guia_id,
                Sesion.aprendiz_id == aprendiz_id,
                Sesion.estado != EstadoSesion.ABANDONADA,
            )
        )
        return resultado.scalar_one_or_none()

    async def de_aprendiz(self, aprendiz_id: uuid.UUID) -> list[Sesion]:
        consulta = (
            self._base()
            .where(Sesion.aprendiz_id == aprendiz_id)
            .options(selectinload(Sesion.guia), selectinload(Sesion.revision))
            # Refresca las relaciones aunque la entidad ya esté en la sesión:
            # sin esto, una revisión recién confirmada no se vería.
            .execution_options(populate_existing=True)
        )
        resultado = await self._sesion.execute(consulta)
        return list(resultado.scalars().all())
