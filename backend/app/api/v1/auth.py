"""Router de autenticación (T-002, T-003)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import SesionBD, UsuarioActual
from app.schemas.identidad import (
    LoginRequest,
    RefreshRequest,
    RegistroRequest,
    TokenResponse,
    UsuarioPublico,
)
from app.services.auth import ServicioAuth

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def registro(datos: RegistroRequest, bd: SesionBD) -> TokenResponse:
    """Alta de instructor.

    El rol se asigna en el servidor: enviar `"rol": "ADMIN"` en el cuerpo no
    escala privilegios porque el esquema de entrada no tiene ese campo.
    """
    return await ServicioAuth(bd).registrar_docente(datos)


@router.post("/login", response_model=TokenResponse)
async def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()], bd: SesionBD
) -> TokenResponse:
    """Inicio de sesión (OAuth2 password flow).

    `username` transporta el correo. Ante credenciales incorrectas se devuelve
    siempre el mismo mensaje, sin revelar si la cuenta existe.
    """
    return await ServicioAuth(bd).login(formulario.username, formulario.password)


@router.post("/login-json", response_model=TokenResponse, include_in_schema=False)
async def login_json(datos: LoginRequest, bd: SesionBD) -> TokenResponse:
    """Variante en JSON, más cómoda para el frontend."""
    return await ServicioAuth(bd).login(datos.email, datos.password)


@router.post("/refresh", response_model=TokenResponse)
async def refrescar(datos: RefreshRequest, bd: SesionBD) -> TokenResponse:
    return await ServicioAuth(bd).refrescar(datos.refresh_token)


@router.get("/yo", response_model=UsuarioPublico)
async def yo(usuario: UsuarioActual) -> UsuarioPublico:
    return UsuarioPublico.model_validate(usuario)
