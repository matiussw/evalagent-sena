"""Servicio del dominio académico: fichas, inscripciones, guías y rúbricas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hashear_password
from app.models.academico import CriterioRubrica, Ficha, Guia, Inscripcion, Rubrica
from app.models.enums import EstadoFicha, EstadoGuia, RolUsuario
from app.models.identidad import Usuario
from app.repositories.academico import (
    RepositorioFichas,
    RepositorioGuias,
    RepositorioInscripciones,
    RepositorioUsuarios,
)
from app.schemas.academico import (
    FichaActualizar,
    FichaCrear,
    GuiaActualizar,
    GuiaCrear,
    InscripcionCrear,
    RubricaCrear,
)
from app.services.errores import Conflicto, NoEncontrado, ReglaDeNegocio, SinPermiso


class ServicioAcademico:
    def __init__(self, sesion: AsyncSession, institucion_id: uuid.UUID) -> None:
        self._sesion = sesion
        self.fichas = RepositorioFichas(sesion, institucion_id)
        self.guias = RepositorioGuias(sesion, institucion_id)
        self.inscripciones = RepositorioInscripciones(sesion, institucion_id)
        self.usuarios = RepositorioUsuarios(sesion, institucion_id)
        self._institucion_id = institucion_id

    # ------------------------------------------------------------- fichas
    async def crear_ficha(self, datos: FichaCrear, docente: Usuario) -> Ficha:
        if await self.fichas.por_codigo(datos.codigo):
            raise Conflicto(
                f"Ya existe una ficha con el código {datos.codigo} en tu institución"
            )
        ficha = Ficha(**datos.model_dump(), docente_id=docente.id)
        return await self.fichas.crear(ficha)

    async def obtener_ficha_propia(self, ficha_id: uuid.UUID, docente: Usuario) -> Ficha:
        """Ficha del docente autenticado.

        Si es de otro docente devuelve 404 igual que si no existiera: dentro de
        una institución tampoco se confirma la existencia de recursos ajenos.
        """
        ficha = await self.fichas.obtener(ficha_id)
        if ficha is None or ficha.docente_id != docente.id:
            raise NoEncontrado("Ficha no encontrada")
        return ficha

    async def actualizar_ficha(
        self, ficha_id: uuid.UUID, datos: FichaActualizar, docente: Usuario
    ) -> Ficha:
        ficha = await self.obtener_ficha_propia(ficha_id, docente)
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(ficha, campo, valor)
        await self._sesion.flush()
        return ficha

    async def archivar_ficha(self, ficha_id: uuid.UUID, docente: Usuario) -> Ficha:
        ficha = await self.obtener_ficha_propia(ficha_id, docente)
        ficha.estado = EstadoFicha.ARCHIVADA
        await self._sesion.flush()
        return ficha

    # ------------------------------------------------------ inscripciones
    async def inscribir(
        self, ficha_id: uuid.UUID, datos: InscripcionCrear, docente: Usuario
    ) -> Inscripcion:
        """Inscribe un aprendiz; crea su cuenta si aún no la tiene."""
        ficha = await self.obtener_ficha_propia(ficha_id, docente)

        aprendiz = await self.usuarios.por_email(datos.email)
        if aprendiz is None:
            aprendiz = Usuario(
                nombre=datos.nombre or datos.email.split("@")[0],
                email=datos.email.lower(),
                # Contraseña temporal aleatoria: el aprendiz la restablece.
                password_hash=hashear_password(uuid.uuid4().hex),
                rol=RolUsuario.APRENDIZ,
                institucion_id=self._institucion_id,
            )
            self._sesion.add(aprendiz)
            await self._sesion.flush()
        elif aprendiz.institucion_id != self._institucion_id:
            raise Conflicto(
                "Ese correo pertenece a una cuenta de otra institución"
            )

        if await self.inscripciones.activa(ficha_id=ficha.id, aprendiz_id=aprendiz.id):
            raise Conflicto("El aprendiz ya está inscrito en esta ficha")

        return await self.inscripciones.crear(
            Inscripcion(ficha_id=ficha.id, aprendiz_id=aprendiz.id)
        )

    # -------------------------------------------------------------- guías
    async def crear_guia(
        self, ficha_id: uuid.UUID, datos: GuiaCrear, docente: Usuario
    ) -> Guia:
        ficha = await self.obtener_ficha_propia(ficha_id, docente)
        return await self.guias.crear(Guia(**datos.model_dump(), ficha_id=ficha.id))

    async def obtener_guia_propia(self, guia_id: uuid.UUID, docente: Usuario) -> Guia:
        guia = await self.guias.con_rubrica(guia_id)
        if guia is None:
            raise NoEncontrado("Guía no encontrada")
        ficha = await self.fichas.obtener(guia.ficha_id)
        if ficha is None or ficha.docente_id != docente.id:
            raise NoEncontrado("Guía no encontrada")
        return guia

    async def actualizar_guia(
        self, guia_id: uuid.UUID, datos: GuiaActualizar, docente: Usuario
    ) -> Guia:
        guia = await self.obtener_guia_propia(guia_id, docente)
        cambios = datos.model_dump(exclude_unset=True)
        for campo, valor in cambios.items():
            setattr(guia, campo, valor)

        if guia.abre_en and guia.cierra_en and guia.cierra_en <= guia.abre_en:
            raise ReglaDeNegocio("`cierra_en` debe ser posterior a `abre_en`")

        await self._sesion.flush()
        return guia

    async def publicar_guia(self, guia_id: uuid.UUID, docente: Usuario) -> Guia:
        """Publica una guía.

        No se publica sin contexto técnico ni sin rúbrica: sin lo primero el
        agente preguntaría de cualquier cosa; sin lo segundo no habría criterio
        con el que calificar.
        """
        guia = await self.obtener_guia_propia(guia_id, docente)

        if not (guia.contexto_tecnico or "").strip():
            raise ReglaDeNegocio(
                "La guía necesita un contexto técnico: es lo que ancla las "
                "preguntas del agente al temario."
            )
        if guia.rubrica is None or not guia.rubrica.criterios:
            raise ReglaDeNegocio(
                "La guía necesita una rúbrica antes de publicarse."
            )
        if not guia.abre_en or not guia.cierra_en:
            raise ReglaDeNegocio("Define la ventana de sustentación de la guía.")

        guia.estado = EstadoGuia.PUBLICADA
        await self._sesion.flush()
        return guia

    # ----------------------------------------------------------- rúbricas
    async def definir_rubrica(
        self, guia_id: uuid.UUID, datos: RubricaCrear, docente: Usuario
    ) -> Rubrica:
        """Reemplaza la rúbrica completa de una guía.

        Editarla no altera las notas ya emitidas: cada sesión guarda su propia
        copia congelada (ADR-007).
        """
        guia = await self.obtener_guia_propia(guia_id, docente)

        if guia.rubrica is not None:
            await self._sesion.delete(guia.rubrica)
            await self._sesion.flush()

        rubrica = Rubrica(
            guia_id=guia.id, umbral_aprobacion=datos.umbral_aprobacion
        )
        rubrica.criterios = [
            CriterioRubrica(
                nombre=c.nombre, descripcion=c.descripcion, peso=c.peso, orden=i
            )
            for i, c in enumerate(datos.criterios)
        ]
        self._sesion.add(rubrica)
        await self._sesion.flush()
        return rubrica

    # ----------------------------------------------------- vista aprendiz
    async def guias_del_aprendiz(self, aprendiz: Usuario) -> list[Guia]:
        return await self.guias.publicadas_para_aprendiz(aprendiz.id)

    async def guia_sustentable(self, guia_id: uuid.UUID, aprendiz: Usuario) -> Guia:
        """Valida que el aprendiz puede sustentar esta guía ahora mismo."""
        guia = await self.guias.con_rubrica(guia_id)
        if guia is None or guia.estado != EstadoGuia.PUBLICADA:
            raise NoEncontrado("Guía no encontrada")

        inscripcion = await self.inscripciones.activa(
            ficha_id=guia.ficha_id, aprendiz_id=aprendiz.id
        )
        if inscripcion is None:
            raise SinPermiso("No estás inscrito en la ficha de esta guía")

        ahora = datetime.now(UTC)
        if guia.abre_en and ahora < guia.abre_en:
            raise SinPermiso("La ventana de sustentación aún no ha abierto")
        if guia.cierra_en and ahora > guia.cierra_en:
            raise SinPermiso("La ventana de sustentación está cerrada")

        return guia


def calcular_nota(puntuaciones: dict[str, int], rubrica_congelada: dict) -> float:
    """Nota ponderada según los pesos de la rúbrica congelada.

    Cada criterio se puntúa de 0 a 10 y pondera según su peso, de modo que la
    nota resultante va de 0 a 100.
    """
    total = 0.0
    for criterio in rubrica_congelada.get("criterios", []):
        puntuacion = puntuaciones.get(criterio["nombre"], 0)
        total += (puntuacion / 10) * criterio["peso"]
    return round(total, 2)
