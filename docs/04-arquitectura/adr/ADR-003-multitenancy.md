# ADR-003 · Multi-tenancy por columna discriminadora

**Estado:** ✅ Aceptada · **Fecha:** 2026-08-02

## Contexto

La plataforma debe alojar varias instituciones (centros de formación) en la misma instancia,
con aislamiento estricto: una fuga de datos entre centros es un incidente de protección de
datos personales, no un bug menor.

Hay tres patrones clásicos de aislamiento y la elección condiciona el esquema, las
migraciones y el despliegue.

## Decisión

**Columna discriminadora `institucion_id` en las tablas raíz**, con estas garantías:

1. El identificador de institución viaja en el *claim* `tid` del JWT.
2. Los esquemas Pydantic de entrada **no exponen** `institucion_id`. Es imposible que el
   cliente lo envíe.
3. Un `RepositorioTenant` base inyecta `WHERE institucion_id = :tid` en toda lectura y
   escritura. Ningún servicio construye consultas sin pasar por él.
4. El acceso a un recurso de otro tenant devuelve `404`, no `403`, para no confirmar su
   existencia.
5. Un test parametrizado recorre **todos** los endpoints de dominio verificando el `404`.

## Alternativas consideradas

| Alternativa | Ventaja | Por qué se descartó |
|---|---|---|
| **Base de datos por tenant** | Aislamiento físico total | Migrar N bases en cada despliegue; inviable para un equipo de una persona |
| **Esquema Postgres por tenant** | Buen aislamiento, una sola base | Alembic con esquemas dinámicos es frágil; la complejidad no se justifica para el volumen esperado (decenas de centros) |
| **Row Level Security de Postgres** | Aislamiento en la propia base, imposible de saltar desde la aplicación | Sólida, pero obliga a gestionar el contexto de sesión de Postgres en un pool async — fuente conocida de errores sutiles. **Candidata para una v3.** |

## Consecuencias

**Positivas**
- Una sola base, una sola cadena de migraciones.
- Añadir una institución es un `INSERT`, no un despliegue.
- Consultas entre tenants (métricas globales del producto) siguen siendo posibles para el rol `ADMIN`.

**Negativas**
- El aislamiento depende de la disciplina de la capa de aplicación. **Un servicio que
  construya una consulta sin pasar por el repositorio base abre una fuga.**
  Mitigación: el test parametrizado sobre todos los endpoints es obligatorio en CI, y
  cualquier endpoint nuevo debe añadirse a él.
- Un error en el filtro afecta a todos los tenants a la vez.

## Verificación

KPI **K8** = 0 incidencias de acceso cruzado. Test parametrizado en CI con cobertura del
100 % de los endpoints de dominio (T-004).
