"""Servicio de sustentación y revisión humana (T-007, T-011).

Aquí vive la regla más importante del sistema: **la única vía por la que una
sesión llega a CALIFICADA es `ServicioRevision.confirmar`**. No existe ninguna
otra ruta de código que asigne ese estado (ADR-006, criterio de aceptación de
T-011).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import crear_ticket_ws
from app.models.academico import Ficha, Guia
from app.models.enums import AccionAuditoria, EstadoSesion, RolTurno
from app.models.identidad import Usuario
from app.models.sustentacion import EventoAuditoria, Revision, Sesion, TurnoConversacion
from app.repositories.academico import RepositorioFichas, RepositorioSesiones
from app.schemas.sustentacion import RevisionConfirmar
from app.services.academico import ServicioAcademico, calcular_nota
from app.services.errores import Conflicto, NoEncontrado, ReglaDeNegocio

_settings = get_settings()


class ServicioSesion:
    def __init__(self, sesion: AsyncSession, institucion_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._institucion_id = institucion_id
        self.sesiones = RepositorioSesiones(sesion, institucion_id)
        self.fichas = RepositorioFichas(sesion, institucion_id)
        self._academico = ServicioAcademico(sesion, institucion_id)

    async def iniciar(self, guia_id: uuid.UUID, aprendiz: Usuario) -> tuple[Sesion, Guia, str]:
        """Crea la sesión y emite el ticket del canal de voz."""
        guia = await self._academico.guia_sustentable(guia_id, aprendiz)

        previa = await self.sesiones.activa_de_aprendiz(guia_id=guia.id, aprendiz_id=aprendiz.id)
        if previa is not None:
            raise Conflicto("Ya sustentaste esta guía")

        if guia.rubrica is None:
            raise ReglaDeNegocio("La guía no tiene rúbrica configurada")

        ahora = datetime.now(UTC)
        sesion = Sesion(
            guia_id=guia.id,
            aprendiz_id=aprendiz.id,
            estado=EstadoSesion.INICIADA,
            # Copia inmutable: editar la rúbrica después no invalida esta nota.
            rubrica_congelada=guia.rubrica.a_dict(),
            consentimiento_aceptado_en=ahora,
            iniciada_en=ahora,
            ultimo_latido=ahora,
        )
        await self.sesiones.crear(sesion)
        await self._auditar(
            AccionAuditoria.SESION_INICIADA, sesion_id=sesion.id, actor_id=aprendiz.id
        )

        ticket = crear_ticket_ws(sesion_id=sesion.id, aprendiz_id=aprendiz.id, jti=uuid.uuid4().hex)
        return sesion, guia, ticket

    async def obtener_para_aprendiz(self, sesion_id: uuid.UUID, aprendiz: Usuario) -> Sesion:
        sesion = await self.sesiones.con_turnos(sesion_id)
        if sesion is None or sesion.aprendiz_id != aprendiz.id:
            raise NoEncontrado("Sesión no encontrada")
        return sesion

    async def obtener_para_docente(self, sesion_id: uuid.UUID, docente: Usuario) -> Sesion:
        """Solo el docente dueño de la ficha de la guía puede verla."""
        sesion = await self.sesiones.con_turnos(sesion_id)
        if sesion is None:
            raise NoEncontrado("Sesión no encontrada")

        ficha = await self.fichas.obtener(sesion.guia.ficha_id)
        if ficha is None or ficha.docente_id != docente.id:
            raise NoEncontrado("Sesión no encontrada")
        return sesion

    async def registrar_turno(
        self,
        sesion: Sesion,
        *,
        rol: RolTurno,
        contenido: str,
        latencia_ms: int | None = None,
    ) -> TurnoConversacion:
        orden = len(sesion.turnos) if sesion.turnos else await self._siguiente_orden(sesion.id)
        turno = TurnoConversacion(
            sesion_id=sesion.id,
            orden=orden,
            rol=rol,
            contenido=contenido,
            latencia_ms=latencia_ms,
        )
        self._sesion.add(turno)

        if sesion.estado == EstadoSesion.INICIADA:
            sesion.estado = EstadoSesion.EN_CURSO
        sesion.ultimo_latido = datetime.now(UTC)

        await self._sesion.flush()
        return turno

    async def _siguiente_orden(self, sesion_id: uuid.UUID) -> int:
        from sqlalchemy import func

        resultado = await self._sesion.execute(
            select(func.coalesce(func.max(TurnoConversacion.orden), -1) + 1).where(
                TurnoConversacion.sesion_id == sesion_id
            )
        )
        return int(resultado.scalar_one())

    async def cerrar(
        self,
        sesion: Sesion,
        *,
        puntuaciones_agente: dict[str, int] | None,
        modelo_llm: str,
        version_prompt: str,
    ) -> Sesion:
        """Cierra la conversación.

        Deja la sesión en PENDIENTE_REVISION, **nunca** en CALIFICADA: la nota
        no existe hasta que un instructor la confirma.
        """
        sesion.estado = EstadoSesion.PENDIENTE_REVISION
        sesion.puntuaciones_agente = puntuaciones_agente
        sesion.modelo_llm = modelo_llm
        sesion.version_prompt = version_prompt
        sesion.finalizada_en = datetime.now(UTC)
        await self._sesion.flush()
        await self._auditar(
            AccionAuditoria.SESION_FINALIZADA,
            sesion_id=sesion.id,
            actor_id=sesion.aprendiz_id,
        )
        return sesion

    async def latido(self, sesion: Sesion) -> None:
        sesion.ultimo_latido = datetime.now(UTC)
        await self._sesion.flush()

    async def expirar_inactivas(self) -> int:
        """Marca como ABANDONADAS las sesiones sin latido.

        Pensada para una tarea programada. Devuelve cuántas se marcaron.
        """
        limite = datetime.now(UTC) - timedelta(minutes=_settings.MINUTOS_SESION_INACTIVA)
        resultado = await self._sesion.execute(
            update(Sesion)
            .where(
                Sesion.estado.in_([EstadoSesion.INICIADA, EstadoSesion.EN_CURSO]),
                Sesion.ultimo_latido < limite,
            )
            .values(estado=EstadoSesion.ABANDONADA, finalizada_en=datetime.now(UTC))
        )
        return resultado.rowcount or 0

    async def _auditar(
        self,
        accion: AccionAuditoria,
        *,
        sesion_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        detalle: dict | None = None,
    ) -> None:
        self._sesion.add(
            EventoAuditoria(sesion_id=sesion_id, actor_id=actor_id, accion=accion, detalle=detalle)
        )
        await self._sesion.flush()


class ServicioRevision:
    """Confirmación humana de la calificación (ADR-006).

    Es el único punto del sistema que puede llevar una sesión a CALIFICADA.
    """

    def __init__(self, sesion: AsyncSession, institucion_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._servicio_sesion = ServicioSesion(sesion, institucion_id)

    async def pendiente(self, sesion_id: uuid.UUID, docente: Usuario) -> Sesion:
        sesion = await self._servicio_sesion.obtener_para_docente(sesion_id, docente)
        if sesion.estado not in (
            EstadoSesion.PENDIENTE_REVISION,
            EstadoSesion.EN_RECLAMACION,
            EstadoSesion.CALIFICADA,
        ):
            raise Conflicto(f"La sesión está en estado {sesion.estado} y no admite revisión")
        return sesion

    async def confirmar(
        self, sesion_id: uuid.UUID, datos: RevisionConfirmar, docente: Usuario
    ) -> tuple[Revision, dict[str, dict[str, int]]]:
        sesion = await self.pendiente(sesion_id, docente)

        criterios = {c["nombre"] for c in sesion.rubrica_congelada.get("criterios", [])}
        recibidos = set(datos.puntuaciones_finales)
        if recibidos != criterios:
            raise ReglaDeNegocio(
                "Las puntuaciones deben cubrir exactamente los criterios de la "
                f"rúbrica. Faltan: {sorted(criterios - recibidos)}. "
                f"Sobran: {sorted(recibidos - criterios)}."
            )

        nota = calcular_nota(datos.puntuaciones_finales, sesion.rubrica_congelada)
        umbral = sesion.rubrica_congelada.get("umbral_aprobacion", 60)

        propuesta = sesion.puntuaciones_agente or {}
        diferencias = {
            nombre: {"agente": propuesta[nombre], "final": final}
            for nombre, final in datos.puntuaciones_finales.items()
            if nombre in propuesta and propuesta[nombre] != final
        }

        revision = Revision(
            sesion_id=sesion.id,
            revisor_id=docente.id,
            puntuaciones_finales=datos.puntuaciones_finales,
            retroalimentacion=datos.retroalimentacion,
            nota_final=nota,
            aprobado=nota >= umbral,
            confirmada_en=datetime.now(UTC),
        )
        self._sesion.add(revision)

        # Única asignación de CALIFICADA en todo el sistema.
        sesion.estado = EstadoSesion.CALIFICADA

        await self._sesion.flush()
        await self._servicio_sesion._auditar(
            AccionAuditoria.NOTA_CONFIRMADA,
            sesion_id=sesion.id,
            actor_id=docente.id,
            detalle={
                "nota_final": nota,
                "aprobado": revision.aprobado,
                "diferencias_con_agente": diferencias,
            },
        )
        return revision, diferencias

    async def reclamar(self, sesion_id: uuid.UUID, aprendiz: Usuario) -> Sesion:
        sesion = await self._servicio_sesion.obtener_para_aprendiz(sesion_id, aprendiz)
        if sesion.estado != EstadoSesion.CALIFICADA:
            raise Conflicto("Solo se puede reclamar una sesión ya calificada")

        sesion.estado = EstadoSesion.EN_RECLAMACION
        await self._sesion.flush()
        await self._servicio_sesion._auditar(
            AccionAuditoria.RECLAMACION_ABIERTA,
            sesion_id=sesion.id,
            actor_id=aprendiz.id,
        )
        return sesion


async def ficha_de_sesion(sesion_db: AsyncSession, sesion: Sesion) -> Ficha | None:
    resultado = await sesion_db.execute(
        select(Ficha).join(Guia, Guia.ficha_id == Ficha.id).where(Guia.id == sesion.guia_id)
    )
    return resultado.scalar_one_or_none()
