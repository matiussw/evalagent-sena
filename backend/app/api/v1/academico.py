"""Routers del dominio académico: fichas, inscripciones, guías y rúbricas."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Aprendiz, Docente, InstitucionActual, SesionBD, UsuarioActual
from app.models.enums import RolUsuario
from app.schemas.academico import (
    FichaActualizar,
    FichaCrear,
    FichaPublica,
    GuiaActualizar,
    GuiaCrear,
    GuiaDetalle,
    GuiaPublica,
    InscripcionCrear,
    InscripcionPublica,
    RubricaCrear,
    RubricaPublica,
)
from app.services.academico import ServicioAcademico

router = APIRouter(tags=["Gestión académica"])


def _servicio(bd: SesionBD, institucion_id: InstitucionActual) -> ServicioAcademico:
    return ServicioAcademico(bd, institucion_id)


Servicio = Annotated[ServicioAcademico, Depends(_servicio)]


# --------------------------------------------------------------------------- #
# Fichas
# --------------------------------------------------------------------------- #

@router.post("/fichas", response_model=FichaPublica, status_code=status.HTTP_201_CREATED)
async def crear_ficha(datos: FichaCrear, docente: Docente, svc: Servicio) -> FichaPublica:
    ficha = await svc.crear_ficha(datos, docente)
    return FichaPublica.model_validate(ficha)


@router.get("/fichas", response_model=list[FichaPublica])
async def listar_fichas(
    usuario: UsuarioActual,
    svc: Servicio,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[FichaPublica]:
    """El docente ve las suyas; el aprendiz, solo aquellas donde está inscrito."""
    if usuario.rol == RolUsuario.APRENDIZ:
        fichas = await svc.fichas.donde_esta_inscrito(usuario.id)
    else:
        fichas = await svc.fichas.de_docente(
            usuario.id, offset=(pagina - 1) * tamano, limite=tamano
        )
    return [FichaPublica.model_validate(f) for f in fichas]


@router.get("/fichas/{ficha_id}", response_model=FichaPublica)
async def obtener_ficha(
    ficha_id: uuid.UUID, docente: Docente, svc: Servicio
) -> FichaPublica:
    return FichaPublica.model_validate(await svc.obtener_ficha_propia(ficha_id, docente))


@router.patch("/fichas/{ficha_id}", response_model=FichaPublica)
async def actualizar_ficha(
    ficha_id: uuid.UUID, datos: FichaActualizar, docente: Docente, svc: Servicio
) -> FichaPublica:
    return FichaPublica.model_validate(
        await svc.actualizar_ficha(ficha_id, datos, docente)
    )


@router.post("/fichas/{ficha_id}/archivar", response_model=FichaPublica)
async def archivar_ficha(
    ficha_id: uuid.UUID, docente: Docente, svc: Servicio
) -> FichaPublica:
    return FichaPublica.model_validate(await svc.archivar_ficha(ficha_id, docente))


# --------------------------------------------------------------------------- #
# Inscripciones
# --------------------------------------------------------------------------- #

@router.post(
    "/fichas/{ficha_id}/inscripciones",
    response_model=InscripcionPublica,
    status_code=status.HTTP_201_CREATED,
)
async def inscribir_aprendiz(
    ficha_id: uuid.UUID, datos: InscripcionCrear, docente: Docente, svc: Servicio
) -> InscripcionPublica:
    inscripcion = await svc.inscribir(ficha_id, datos, docente)
    return InscripcionPublica.model_validate(inscripcion)


@router.get("/fichas/{ficha_id}/inscripciones", response_model=list[InscripcionPublica])
async def listar_inscripciones(
    ficha_id: uuid.UUID, docente: Docente, svc: Servicio
) -> list[InscripcionPublica]:
    ficha = await svc.obtener_ficha_propia(ficha_id, docente)
    inscripciones = await svc.inscripciones.listar(ficha_id=ficha.id, limite=100)
    return [InscripcionPublica.model_validate(i) for i in inscripciones]


# --------------------------------------------------------------------------- #
# Guías
# --------------------------------------------------------------------------- #

@router.post(
    "/fichas/{ficha_id}/guias",
    response_model=GuiaPublica,
    status_code=status.HTTP_201_CREATED,
)
async def crear_guia(
    ficha_id: uuid.UUID, datos: GuiaCrear, docente: Docente, svc: Servicio
) -> GuiaPublica:
    return GuiaPublica.model_validate(await svc.crear_guia(ficha_id, datos, docente))


@router.get("/fichas/{ficha_id}/guias", response_model=list[GuiaPublica])
async def listar_guias_de_ficha(
    ficha_id: uuid.UUID, docente: Docente, svc: Servicio
) -> list[GuiaPublica]:
    ficha = await svc.obtener_ficha_propia(ficha_id, docente)
    guias = await svc.guias.listar(ficha_id=ficha.id, limite=100)
    return [GuiaPublica.model_validate(g) for g in guias]


@router.get("/mis-guias", response_model=list[GuiaPublica])
async def mis_guias(aprendiz: Aprendiz, svc: Servicio) -> list[GuiaPublica]:
    """Guías publicadas de las fichas donde el aprendiz está inscrito."""
    return [GuiaPublica.model_validate(g) for g in await svc.guias_del_aprendiz(aprendiz)]


@router.get("/guias/{guia_id}", response_model=GuiaDetalle)
async def obtener_guia(
    guia_id: uuid.UUID, usuario: UsuarioActual, svc: Servicio
) -> GuiaDetalle:
    if usuario.rol == RolUsuario.APRENDIZ:
        guia = await svc.guia_sustentable(guia_id, usuario)
    else:
        guia = await svc.obtener_guia_propia(guia_id, usuario)
    return GuiaDetalle.model_validate(guia)


@router.patch("/guias/{guia_id}", response_model=GuiaPublica)
async def actualizar_guia(
    guia_id: uuid.UUID, datos: GuiaActualizar, docente: Docente, svc: Servicio
) -> GuiaPublica:
    return GuiaPublica.model_validate(await svc.actualizar_guia(guia_id, datos, docente))


@router.post("/guias/{guia_id}/publicar", response_model=GuiaPublica)
async def publicar_guia(
    guia_id: uuid.UUID, docente: Docente, svc: Servicio
) -> GuiaPublica:
    """Publica la guía. Exige contexto técnico, rúbrica y ventana definida."""
    return GuiaPublica.model_validate(await svc.publicar_guia(guia_id, docente))


# --------------------------------------------------------------------------- #
# Rúbricas
# --------------------------------------------------------------------------- #

@router.put("/guias/{guia_id}/rubrica", response_model=RubricaPublica)
async def definir_rubrica(
    guia_id: uuid.UUID, datos: RubricaCrear, docente: Docente, svc: Servicio
) -> RubricaPublica:
    """Reemplaza la rúbrica completa. Los pesos deben sumar 100."""
    return RubricaPublica.model_validate(
        await svc.definir_rubrica(guia_id, datos, docente)
    )


@router.get("/guias/{guia_id}/rubrica", response_model=RubricaPublica)
async def obtener_rubrica(
    guia_id: uuid.UUID, usuario: UsuarioActual, svc: Servicio
) -> RubricaPublica:
    from app.services.errores import NoEncontrado

    if usuario.rol == RolUsuario.APRENDIZ:
        guia = await svc.guia_sustentable(guia_id, usuario)
    else:
        guia = await svc.obtener_guia_propia(guia_id, usuario)

    if guia.rubrica is None:
        raise NoEncontrado("La guía todavía no tiene rúbrica")
    return RubricaPublica.model_validate(guia.rubrica)
