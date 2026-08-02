# T-006 · Guías de aprendizaje con contexto para el agente

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-07](../02-backlog/02-historias-usuario.md#hu-07--publicar-una-guía-de-aprendizaje) |
| **Épica** | E2 · Gestión académica |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/v1/guias.py` |
| **Estado** | `Por hacer` |

## Descripción

La guía sustituye a los ficheros `proyectos/*.md` de la versión 1. Es el contenido que el
instructor publica y, sobre todo, **el contexto que ancla las preguntas del agente al
temario real**. Migrar esto de sistema de ficheros a base de datos es lo que permite que
varios instructores convivan en la misma instancia.

## Alcance técnico

- Modelo `Guia`: `titulo`, `descripcion`, `contexto_tecnico` (texto largo, Markdown),
  `num_preguntas` (por defecto 8), `estado` (`BORRADOR` · `PUBLICADA` · `CERRADA`),
  `abre_en`, `cierra_en`, `ficha_id`.
- Endpoints CRUD + `POST /{id}/publicar`.
- Los aprendices solo ven guías `PUBLICADA` de fichas donde están inscritos.
- Validación: `cierra_en > abre_en`; no se publica sin `contexto_tecnico` ni sin rúbrica.
- Script de migración que convierte los `proyectos/*.md` existentes en guías.

## Criterios de aceptación

- [ ] Una guía en `BORRADOR` no aparece en el listado del aprendiz.
- [ ] Publicar sin `contexto_tecnico` devuelve `422`.
- [ ] Publicar sin rúbrica asociada devuelve `422`.
- [ ] `cierra_en` anterior a `abre_en` devuelve `422`.
- [ ] El script convierte `proyectos/gestion-tareas.md` en una guía con su contexto íntegro.
- [ ] `num_preguntas` fuera del rango 3–20 devuelve `422`.

## Definición de terminado

CRUD en OpenAPI · 6 tests · script de migración probado con los dos ficheros existentes.

## Dependencias

**Requiere:** T-005. **Bloquea:** T-007, T-010.
