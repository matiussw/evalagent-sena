"""Errores de dominio.

Los servicios lanzan estas excepciones sin saber nada de HTTP; un manejador en
`main.py` las traduce a respuestas RFC 7807. Así la lógica de negocio no queda
acoplada a FastAPI.
"""


class ErrorDominio(Exception):
    estado: int = 400
    tipo: str = "error-dominio"
    titulo: str = "Error de dominio"

    def __init__(self, detalle: str | None = None) -> None:
        self.detalle = detalle or self.titulo
        super().__init__(self.detalle)


class NoEncontrado(ErrorDominio):
    """404. También se usa para recursos de otro tenant.

    Devolver 404 en lugar de 403 evita confirmar que el recurso existe.
    """

    estado = 404
    tipo = "no-encontrado"
    titulo = "Recurso no encontrado"


class SinPermiso(ErrorDominio):
    estado = 403
    tipo = "sin-permiso"
    titulo = "No tienes permiso para esta acción"


class Conflicto(ErrorDominio):
    estado = 409
    tipo = "conflicto"
    titulo = "Conflicto con el estado actual"


class ReglaDeNegocio(ErrorDominio):
    estado = 422
    tipo = "regla-de-negocio"
    titulo = "La operación incumple una regla de negocio"


class CredencialesInvalidas(ErrorDominio):
    estado = 401
    tipo = "credenciales-invalidas"
    titulo = "Credenciales inválidas"


class DemasiadosIntentos(ErrorDominio):
    estado = 429
    tipo = "demasiados-intentos"
    titulo = "Demasiados intentos"
