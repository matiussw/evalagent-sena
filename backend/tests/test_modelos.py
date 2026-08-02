"""Tests del mapeo de modelos y de las reglas de integridad (T-001)."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

from app import models


def test_los_mapeos_son_validos() -> None:
    """Detecta relaciones mal declaradas antes de tocar la base de datos."""
    configure_mappers()


def test_estan_todas_las_tablas_del_erd() -> None:
    esperadas = {
        "instituciones",
        "usuarios",
        "fichas",
        "inscripciones",
        "guias",
        "rubricas",
        "criterios_rubrica",
        "sesiones",
        "turnos_conversacion",
        "revisiones",
        "eventos_auditoria",
    }
    assert esperadas <= set(models.Base.metadata.tables)


def test_la_sesion_no_almacena_audio() -> None:
    """RNF-09: solo se persiste la transcripción textual, nunca el audio crudo."""
    columnas = {c.name for c in models.Sesion.__table__.columns}
    prohibidas = {"audio", "audio_b64", "audio_path", "grabacion", "wav"}

    assert not (columnas & prohibidas)


def test_ninguna_tabla_almacena_audio() -> None:
    for tabla in models.Base.metadata.tables.values():
        for columna in tabla.columns:
            assert "audio" not in columna.name.lower(), (
                f"{tabla.name}.{columna.name} sugiere almacenamiento de audio"
            )


def test_el_repr_de_usuario_no_filtra_el_hash() -> None:
    usuario = models.Usuario(
        nombre="Carolina",
        email="carolina@sena.edu.co",
        password_hash="$2b$12$secretoquenodebesalir",
        rol=models.RolUsuario.DOCENTE,
    )
    assert "secretoquenodebesalir" not in repr(usuario)
    assert "carolina@sena.edu.co" in repr(usuario)


def test_codigo_de_ficha_unico_por_institucion_no_global() -> None:
    """El mismo código puede repetirse entre centros, pero no dentro de uno."""
    restricciones = {
        c.name: {col.name for col in c.columns}
        for c in models.Ficha.__table__.constraints
        if c.name and c.name.startswith("uq_")
    }
    assert restricciones["uq_ficha_institucion_codigo"] == {"institucion_id", "codigo"}


def test_una_guia_tiene_como_mucho_una_rubrica() -> None:
    guia_id = models.Rubrica.__table__.columns["guia_id"]
    assert guia_id.unique is True


def test_una_sesion_tiene_como_mucho_una_revision() -> None:
    """ADR-006: la revisión es 1:1 y su existencia habilita el estado CALIFICADA."""
    sesion_id = models.Revision.__table__.columns["sesion_id"]
    assert sesion_id.unique is True


def test_indice_parcial_impide_sustentar_dos_veces_la_misma_guia() -> None:
    """RI-7: una sola sesión no abandonada por guía y aprendiz."""
    indices = {i.name: i for i in models.Sesion.__table__.indexes}
    idx = indices["idx_sesion_unica_por_guia"]

    assert idx.unique is True
    assert {c.name for c in idx.columns} == {"guia_id", "aprendiz_id"}
    # El índice es parcial: una sesión ABANDONADA no bloquea un nuevo intento.
    assert "ABANDONADA" in str(idx.dialect_options["postgresql"]["where"])


def test_rubrica_congelada_es_obligatoria() -> None:
    """ADR-007: sin copia de la rúbrica la nota sería indefendible a posteriori."""
    assert models.Sesion.__table__.columns["rubrica_congelada"].nullable is False


def test_el_consentimiento_es_obligatorio_para_crear_sesion() -> None:
    assert models.Sesion.__table__.columns["consentimiento_aceptado_en"].nullable is False


@pytest.mark.parametrize(
    ("tabla", "columna"),
    [
        ("usuarios", "institucion_id"),
        ("fichas", "institucion_id"),
    ],
)
def test_las_tablas_raiz_llevan_discriminador_de_tenant(tabla: str, columna: str) -> None:
    """ADR-003: el aislamiento se apoya en esta columna."""
    assert models.Base.metadata.tables[tabla].columns[columna].nullable is False


def test_borrar_institucion_con_usuarios_esta_restringido() -> None:
    fk = next(iter(models.Usuario.__table__.columns["institucion_id"].foreign_keys))
    assert fk.ondelete == "RESTRICT"


def test_borrar_una_ficha_arrastra_sus_guias() -> None:
    fk = next(iter(models.Guia.__table__.columns["ficha_id"].foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_todas_las_tablas_tienen_auditoria_temporal() -> None:
    for tabla in models.Base.metadata.tables.values():
        columnas = set(tabla.columns.keys())
        assert {"id", "creado_en", "actualizado_en"} <= columnas, tabla.name


def test_inspeccion_de_relaciones_de_sesion() -> None:
    relaciones = {r.key for r in inspect(models.Sesion).relationships}
    assert {"guia", "aprendiz", "turnos", "revision"} <= relaciones
