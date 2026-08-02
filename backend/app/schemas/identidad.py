"""Esquemas de autenticación e identidad (T-002, T-003)."""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RolUsuario
from app.schemas.comun import EsquemaBase


class RegistroRequest(BaseModel):
    """Alta de instructor.

    No incluye `rol` a propósito: el servidor asigna siempre DOCENTE. Aunque el
    cliente lo envíe, Pydantic lo descarta y no hay escalada de privilegios.
    """

    nombre: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    institucion_id: uuid.UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UsuarioPublico(EsquemaBase):
    """Vista de un usuario hacia el exterior. Nunca incluye `password_hash`."""

    id: uuid.UUID
    nombre: str
    email: EmailStr
    rol: RolUsuario
    institucion_id: uuid.UUID


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioPublico


class RefreshRequest(BaseModel):
    refresh_token: str


class InstitucionCrear(BaseModel):
    nombre: str = Field(min_length=3, max_length=200)
    nit: str = Field(min_length=5, max_length=20)


class InstitucionPublica(EsquemaBase):
    id: uuid.UUID
    nombre: str
    nit: str
    activa: bool
