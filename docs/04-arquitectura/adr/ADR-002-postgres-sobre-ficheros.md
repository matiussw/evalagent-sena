# ADR-002 · PostgreSQL en lugar de persistencia en ficheros

**Estado:** ✅ Aceptada · **Fecha:** 2026-08-02 · **Supersede:** la decisión implícita de la v1

## Contexto

La v1 persistía en el sistema de ficheros: guías como `proyectos/*.md`, reportes como
`reportes/*.json`, y el estado de las sesiones activas en un `dict` en memoria de Python.

Esto funcionaba para un instructor en su portátil. No funciona para una plataforma SaaS:

- No hay forma de consultar "todas las sesiones pendientes de revisión de la ficha 2758421"
  sin leer y parsear todos los ficheros.
- No hay integridad referencial: un reporte apunta a un `student_name` en texto libre.
- El estado en memoria se pierde en cada reinicio (deuda **D7**).
- No hay transacciones: una escritura a medias deja el reporte corrupto.
- No hay control de acceso: quien lee el disco lo lee todo.

## Decisión

**PostgreSQL 16 como única fuente de verdad**, con SQLAlchemy 2.0 en modo async y
migraciones versionadas con Alembic.

Se usa **JSONB** para los datos que son inherentemente documentales y no se consultan por
campo: `rubrica_congelada`, `puntuaciones_agente`, `detalle` de auditoría.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| SQLite | Cero infraestructura y suficiente para un centro pequeño. Descartada por la concurrencia de escritura durante sustentaciones simultáneas y porque el despliegue final requiere un servicio gestionado. |
| MongoDB | Encaja con la naturaleza documental de las transcripciones, pero el dominio es fuertemente relacional (institución → ficha → guía → sesión) y perderíamos integridad referencial. |
| Ficheros + índice en SQLite | Lo peor de ambos mundos: dos fuentes de verdad que se desincronizan. |

## Consecuencias

**Positivas**
- Integridad referencial y transacciones.
- Consultas de agregación para el panel de desempeño (HU-14) sin código ad hoc.
- Índices parciales únicos que hacen cumplir reglas de negocio en la base (RI-7).
- Migraciones versionadas y reversibles.
- Cumple el requisito de base de datos del Módulo 8 y de la Entrega 2.

**Negativas**
- Añade un contenedor más al despliegue.
- Exige backups, que antes eran "copiar una carpeta".
- Requiere migrar los datos existentes (script documentado en el modelo de datos, §6).
