"""Routers de sustentación, revisión y resultados (T-007, T-011)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Aprendiz, Docente, InstitucionActual, SesionBD
from app.models.enums import EstadoSesion
from app.schemas.sustentacion import (
    ResultadoAprendiz,
    RevisionConfirmada,
    RevisionConfirmar,
    RevisionPendiente,
    SesionCrear,
    SesionDetalle,
    SesionIniciada,
    SesionPublica,
    TurnoPublico,
)
from app.services.academico import calcular_nota
from app.services.sesion import ServicioRevision, ServicioSesion

router = APIRouter(tags=["Sustentación"])


def _svc_sesion(bd: SesionBD, institucion_id: InstitucionActual) -> ServicioSesion:
    return ServicioSesion(bd, institucion_id)


def _svc_revision(bd: SesionBD, institucion_id: InstitucionActual) -> ServicioRevision:
    return ServicioRevision(bd, institucion_id)


SvcSesion = Annotated[ServicioSesion, Depends(_svc_sesion)]
SvcRevision = Annotated[ServicioRevision, Depends(_svc_revision)]


# --------------------------------------------------------------------------- #
# Aprendiz: sustentar
# --------------------------------------------------------------------------- #

@router.post(
    "/sesiones", response_model=SesionIniciada, status_code=status.HTTP_201_CREATED
)
async def iniciar_sesion(
    datos: SesionCrear, aprendiz: Aprendiz, svc: SvcSesion
) -> SesionIniciada:
    """Inicia una sustentación y devuelve el ticket del canal de voz.

    El ticket caduca en 60 segundos y es de un solo uso.
    """
    sesion, guia, ticket = await svc.iniciar(datos.guia_id, aprendiz)
    return SesionIniciada(
        id=sesion.id,
        estado=sesion.estado,
        guia_titulo=guia.titulo,
        num_preguntas=guia.num_preguntas,
        rubrica_congelada=sesion.rubrica_congelada,
        ws_ticket=ticket,
        ws_url=f"/api/v1/ws/sesiones/{sesion.id}",
    )


@router.post("/sesiones/{sesion_id}/latido", status_code=status.HTTP_204_NO_CONTENT)
async def latido(sesion_id: uuid.UUID, aprendiz: Aprendiz, svc: SvcSesion) -> None:
    sesion = await svc.obtener_para_aprendiz(sesion_id, aprendiz)
    await svc.latido(sesion)


@router.get("/sesiones/{sesion_id}", response_model=SesionDetalle)
async def obtener_sesion(
    sesion_id: uuid.UUID, aprendiz: Aprendiz, svc: SvcSesion
) -> SesionDetalle:
    sesion = await svc.obtener_para_aprendiz(sesion_id, aprendiz)
    return SesionDetalle(
        **SesionPublica.model_validate(sesion).model_dump(),
        rubrica_congelada=sesion.rubrica_congelada,
        turnos=[TurnoPublico.model_validate(t) for t in sesion.turnos],
    )


@router.get("/mis-resultados", response_model=list[ResultadoAprendiz])
async def mis_resultados(aprendiz: Aprendiz, svc: SvcSesion) -> list[ResultadoAprendiz]:
    """Resultados del aprendiz.

    Mientras la sesión no esté CALIFICADA no se devuelve nota alguna — ni
    siquiera la propuesta del agente (ADR-006).
    """
    sesiones = await svc.sesiones.de_aprendiz(aprendiz.id)
    salida: list[ResultadoAprendiz] = []

    for s in sesiones:
        if s.estado == EstadoSesion.CALIFICADA and s.revision is not None:
            salida.append(
                ResultadoAprendiz(
                    sesion_id=s.id,
                    guia_titulo=s.guia.titulo,
                    estado=s.estado,
                    nota_final=float(s.revision.nota_final),
                    aprobado=s.revision.aprobado,
                    desglose=s.revision.puntuaciones_finales,
                    retroalimentacion=s.revision.retroalimentacion,
                )
            )
        else:
            salida.append(
                ResultadoAprendiz(
                    sesion_id=s.id,
                    guia_titulo=s.guia.titulo,
                    estado=s.estado,
                    mensaje=_mensaje_estado(s.estado),
                )
            )
    return salida


def _mensaje_estado(estado: EstadoSesion) -> str:
    return {
        EstadoSesion.INICIADA: "Sustentación sin terminar",
        EstadoSesion.EN_CURSO: "Sustentación en curso",
        EstadoSesion.PENDIENTE_REVISION: "Pendiente de revisión del instructor",
        EstadoSesion.EN_RECLAMACION: "Reclamación en curso",
        EstadoSesion.ABANDONADA: "Sustentación abandonada",
    }.get(estado, "Sin información")


@router.post("/sesiones/{sesion_id}/reclamar", response_model=SesionPublica)
async def reclamar(
    sesion_id: uuid.UUID, aprendiz: Aprendiz, svc: SvcRevision
) -> SesionPublica:
    return SesionPublica.model_validate(await svc.reclamar(sesion_id, aprendiz))


# --------------------------------------------------------------------------- #
# Docente: revisar y confirmar
# --------------------------------------------------------------------------- #

@router.get("/sesiones", response_model=list[SesionPublica])
async def bandeja_de_revision(
    docente: Docente,
    svc: SvcSesion,
    estado: Annotated[EstadoSesion | None, Query()] = None,
    guia_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[SesionPublica]:
    sesiones = await svc.sesiones.listar(estado=estado, guia_id=guia_id, limite=100)
    visibles = []
    for s in sesiones:
        try:
            await svc.obtener_para_docente(s.id, docente)
        except Exception:
            continue
        visibles.append(s)
    return [SesionPublica.model_validate(s) for s in visibles]


@router.get("/sesiones/{sesion_id}/revision", response_model=RevisionPendiente)
async def ver_revision(
    sesion_id: uuid.UUID, docente: Docente, svc: SvcRevision
) -> RevisionPendiente:
    """Transcripción íntegra y propuesta del agente.

    Es el único endpoint que expone `puntuaciones_agente`, y solo al instructor
    dueño de la ficha.
    """
    sesion = await svc.pendiente(sesion_id, docente)
    nota_propuesta = (
        calcular_nota(sesion.puntuaciones_agente, sesion.rubrica_congelada)
        if sesion.puntuaciones_agente
        else None
    )
    return RevisionPendiente(
        sesion_id=sesion.id,
        aprendiz=sesion.aprendiz.nombre,
        guia_titulo=sesion.guia.titulo,
        estado=sesion.estado,
        rubrica_congelada=sesion.rubrica_congelada,
        puntuaciones_agente=sesion.puntuaciones_agente,
        nota_propuesta=nota_propuesta,
        turnos=[TurnoPublico.model_validate(t) for t in sesion.turnos],
    )


@router.post("/sesiones/{sesion_id}/revision", response_model=RevisionConfirmada)
async def confirmar_revision(
    sesion_id: uuid.UUID,
    datos: RevisionConfirmar,
    docente: Docente,
    svc: SvcRevision,
) -> RevisionConfirmada:
    """Confirma la calificación y la publica al aprendiz.

    Es la única vía por la que una sesión llega a CALIFICADA (ADR-006).
    """
    revision, diferencias = await svc.confirmar(sesion_id, datos, docente)
    return RevisionConfirmada(
        sesion_id=revision.sesion_id,
        estado=EstadoSesion.CALIFICADA,
        nota_final=float(revision.nota_final),
        aprobado=revision.aprobado,
        revisor_id=revision.revisor_id,
        confirmada_en=revision.confirmada_en,
        diferencias_con_agente=diferencias,
    )
