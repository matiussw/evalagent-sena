# T-013 · CORS con lista blanca por entorno

| Campo | Valor |
|---|---|
| **Tipo** | 🐞 Bug de seguridad / deuda técnica **D6** |
| **Historia** | Transversal a E1 |
| **Épica** | E6 · Plataforma y despliegue |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 2 pts |
| **Componente** | `backend/app/main.py` · `backend/app/core/config.py` |
| **Estado** | `Por hacer` |

## Descripción

**El defecto:** `main.py` configura `allow_origins=["*"]` junto con
`allow_credentials=True`. Es una combinación inválida según la especificación de CORS y los
navegadores la rechazan; peor aún, si se relaja, permitiría que cualquier sitio hiciera
peticiones autenticadas contra la API.

En la v1 era tolerable porque todo corría en `localhost` sin autenticación. Con JWT y
despliegue público pasa a ser un fallo de seguridad real.

## Alcance técnico

- `CORS_ORIGINS` como lista separada por comas en variable de entorno.
- Desarrollo: `http://localhost:5173`. Producción: dominio público concreto.
- Prohibir explícitamente `*` cuando `allow_credentials=True`: el arranque debe fallar.
- Métodos y cabeceras acotados a los que la API realmente usa.

## Criterios de aceptación

- [ ] Una petición desde un origen no listado es rechazada por CORS.
- [ ] Arrancar con `CORS_ORIGINS=*` y credenciales activas aborta el arranque con error claro.
- [ ] El frontend en `localhost:5173` funciona en desarrollo.
- [ ] `.env.example` documenta la variable.

## Definición de terminado

Test de CORS con origen permitido y denegado · deuda **D6** cerrada.

## Dependencias

**Requiere:** T-003.
