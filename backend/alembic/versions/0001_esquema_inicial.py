"""Esquema inicial de la plataforma SaaS

Crea el dominio completo: identidad multi-tenant, gestión académica con rúbricas
configurables, y sustentación con revisión humana obligatoria.

Sustituye la persistencia en ficheros de la v1 (ADR-002).

Revision ID: 0001_esquema_inicial
Revises:
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = "0001_esquema_inicial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Postgres no borra los tipos ENUM al eliminar la tabla que los usa.
TIPOS_ENUM = (
    "rol_usuario",
    "estado_ficha",
    "estado_inscripcion",
    "estado_guia",
    "estado_sesion",
    "rol_turno",
    "accion_auditoria",
)


def upgrade() -> None:
    op.create_table('instituciones',
    sa.Column('nombre', sa.String(length=200), nullable=False),
    sa.Column('nit', sa.String(length=20), nullable=False),
    sa.Column('activa', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nit')
    )
    op.create_table('usuarios',
    sa.Column('institucion_id', sa.UUID(), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('rol', sa.Enum('ADMIN', 'DOCENTE', 'APRENDIZ', name='rol_usuario'), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['institucion_id'], ['instituciones.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_index('idx_usuario_institucion_rol', 'usuarios', ['institucion_id', 'rol'], unique=False)
    op.create_table('fichas',
    sa.Column('institucion_id', sa.UUID(), nullable=False),
    sa.Column('docente_id', sa.UUID(), nullable=False),
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=200), nullable=False),
    sa.Column('programa', sa.String(length=120), nullable=False),
    sa.Column('trimestre', sa.String(length=10), nullable=False),
    sa.Column('estado', sa.Enum('ACTIVA', 'ARCHIVADA', name='estado_ficha'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['docente_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['institucion_id'], ['instituciones.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('institucion_id', 'codigo', name='uq_ficha_institucion_codigo')
    )
    op.create_index('idx_ficha_docente_estado', 'fichas', ['docente_id', 'estado'], unique=False)
    op.create_table('guias',
    sa.Column('ficha_id', sa.UUID(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('contexto_tecnico', sa.Text(), nullable=True),
    sa.Column('num_preguntas', sa.Integer(), nullable=False),
    sa.Column('estado', sa.Enum('BORRADOR', 'PUBLICADA', 'CERRADA', name='estado_guia'), nullable=False),
    sa.Column('abre_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cierra_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('cierra_en > abre_en', name='ck_guia_ventana_valida'),
    sa.CheckConstraint('num_preguntas BETWEEN 3 AND 20', name='ck_guia_num_preguntas'),
    sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_guia_ficha_estado', 'guias', ['ficha_id', 'estado'], unique=False)
    op.create_table('inscripciones',
    sa.Column('ficha_id', sa.UUID(), nullable=False),
    sa.Column('aprendiz_id', sa.UUID(), nullable=False),
    sa.Column('estado', sa.Enum('ACTIVA', 'RETIRADA', name='estado_inscripcion'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['aprendiz_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ficha_id'], ['fichas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ficha_id', 'aprendiz_id', name='uq_inscripcion_ficha_aprendiz')
    )
    op.create_index('idx_inscripcion_aprendiz', 'inscripciones', ['aprendiz_id', 'estado'], unique=False)
    op.create_table('rubricas',
    sa.Column('guia_id', sa.UUID(), nullable=False),
    sa.Column('umbral_aprobacion', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['guia_id'], ['guias.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('guia_id')
    )
    op.create_table('sesiones',
    sa.Column('guia_id', sa.UUID(), nullable=False),
    sa.Column('aprendiz_id', sa.UUID(), nullable=False),
    sa.Column('estado', sa.Enum('INICIADA', 'EN_CURSO', 'PENDIENTE_REVISION', 'CALIFICADA', 'EN_RECLAMACION', 'ABANDONADA', name='estado_sesion'), nullable=False),
    sa.Column('rubrica_congelada', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('puntuaciones_agente', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('modelo_llm', sa.String(length=80), nullable=True),
    sa.Column('version_prompt', sa.String(length=20), nullable=True),
    sa.Column('preguntas_respondidas', sa.Integer(), nullable=False),
    sa.Column('consentimiento_aceptado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('iniciada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ultimo_latido', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finalizada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['aprendiz_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['guia_id'], ['guias.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sesion_aprendiz', 'sesiones', ['aprendiz_id'], unique=False)
    op.create_index('idx_sesion_guia_estado', 'sesiones', ['guia_id', 'estado'], unique=False)
    op.create_index('idx_sesion_unica_por_guia', 'sesiones', ['guia_id', 'aprendiz_id'], unique=True, postgresql_where=sa.text("estado <> 'ABANDONADA'"))
    op.create_table('criterios_rubrica',
    sa.Column('rubrica_id', sa.UUID(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('peso', sa.Integer(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('peso BETWEEN 1 AND 100', name='ck_criterio_peso'),
    sa.ForeignKeyConstraint(['rubrica_id'], ['rubricas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('eventos_auditoria',
    sa.Column('sesion_id', sa.UUID(), nullable=True),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('accion', sa.Enum('SESION_INICIADA', 'SESION_FINALIZADA', 'SESION_ABANDONADA', 'NOTA_CONFIRMADA', 'RECLAMACION_ABIERTA', 'ACCESO_CRUZADO_BLOQUEADO', name='accion_auditoria'), nullable=False),
    sa.Column('detalle', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['usuarios.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['sesion_id'], ['sesiones.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auditoria_sesion_fecha', 'eventos_auditoria', ['sesion_id', 'creado_en'], unique=False)
    op.create_table('revisiones',
    sa.Column('sesion_id', sa.UUID(), nullable=False),
    sa.Column('revisor_id', sa.UUID(), nullable=False),
    sa.Column('puntuaciones_finales', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('retroalimentacion', sa.Text(), nullable=True),
    sa.Column('nota_final', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('aprobado', sa.Boolean(), nullable=False),
    sa.Column('confirmada_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['revisor_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['sesion_id'], ['sesiones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sesion_id')
    )
    op.create_table('turnos_conversacion',
    sa.Column('sesion_id', sa.UUID(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('rol', sa.Enum('AGENTE', 'APRENDIZ', name='rol_turno'), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('latencia_ms', sa.Integer(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['sesion_id'], ['sesiones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sesion_id', 'orden', name='uq_turno_sesion_orden')
    )
    op.create_index('idx_turno_sesion_orden', 'turnos_conversacion', ['sesion_id', 'orden'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_turno_sesion_orden', table_name='turnos_conversacion')
    op.drop_table('turnos_conversacion')
    op.drop_table('revisiones')
    op.drop_index('idx_auditoria_sesion_fecha', table_name='eventos_auditoria')
    op.drop_table('eventos_auditoria')
    op.drop_table('criterios_rubrica')
    op.drop_index('idx_sesion_unica_por_guia', table_name='sesiones', postgresql_where=sa.text("estado <> 'ABANDONADA'"))
    op.drop_index('idx_sesion_guia_estado', table_name='sesiones')
    op.drop_index('idx_sesion_aprendiz', table_name='sesiones')
    op.drop_table('sesiones')
    op.drop_table('rubricas')
    op.drop_index('idx_inscripcion_aprendiz', table_name='inscripciones')
    op.drop_table('inscripciones')
    op.drop_index('idx_guia_ficha_estado', table_name='guias')
    op.drop_table('guias')
    op.drop_index('idx_ficha_docente_estado', table_name='fichas')
    op.drop_table('fichas')
    op.drop_index('idx_usuario_institucion_rol', table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_table('instituciones')

    for tipo in TIPOS_ENUM:
        op.execute(f"DROP TYPE IF EXISTS {tipo}")
