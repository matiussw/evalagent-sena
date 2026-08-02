# T-011 · Revisión y confirmación humana de la calificación

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-12](../02-backlog/02-historias-usuario.md#hu-12--revisar-y-confirmar-la-calificación) |
| **Épica** | E4 · Evaluación y rúbricas |
| **Prioridad** | 🔴 Crítica |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/v1/revisiones.py` |
| **Estado** | `Por hacer` |

## Descripción

Implementar el **humano en el bucle**. No es una funcionalidad opcional: es lo que hace que
el sistema sea legalmente admisible bajo el Art. 22 del RGPD y el AI Act, que prohíben la
decisión totalmente automatizada con efecto significativo sobre una persona. Ninguna nota
llega al aprendiz sin que un instructor la haya confirmado.

## Alcance técnico

- Modelo `Revision`: `sesion_id`, `revisor_id`, `puntuaciones_finales` (JSONB),
  `puntuaciones_agente` (JSONB, congeladas), `retroalimentacion`, `nota_final`,
  `aprobado`, `confirmada_en`.
- `GET /api/v1/sesiones/{id}/revision` → transcripción + propuesta del agente.
- `POST /api/v1/sesiones/{id}/revision` → confirma y publica.
- Solo el instructor dueño de la ficha puede confirmar.
- Registro de auditoría inmutable: quién, cuándo, y el diferencial entre propuesta y nota final.
- El aprendiz consulta el resultado **solo** si el estado es `CALIFICADA`.
- `POST /api/v1/sesiones/{id}/reclamar` → pasa a `EN_RECLAMACION`.

## Criterios de aceptación

- [ ] Una sesión `PENDIENTE_REVISION` no expone ninguna nota al aprendiz.
- [ ] El aprendiz ve "Pendiente de revisión del instructor" mientras no se confirme.
- [ ] Confirmar cambia el estado a `CALIFICADA` y registra revisor, fecha y diferencias.
- [ ] Un instructor de otra ficha recibe `403` al intentar confirmar.
- [ ] Las puntuaciones propuestas por el agente quedan almacenadas aunque se modifiquen (auditoría).
- [ ] Reclamar mueve la sesión a `EN_RECLAMACION` y notifica al instructor.
- [ ] **No existe ninguna ruta de código** que lleve una sesión a `CALIFICADA` sin revisión humana.

## Definición de terminado

Tests que cubren las 6 transiciones · auditoría verificada · el último criterio validado por
búsqueda exhaustiva en el código.

## Dependencias

**Requiere:** T-009, T-010.

## Referencia

[ADR-006 · Humano en el bucle](../04-arquitectura/adr/ADR-006-humano-en-el-bucle.md) ·
Módulo 6 (Ética, regulación y privacidad).
