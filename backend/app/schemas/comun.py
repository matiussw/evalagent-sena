"""Esquemas transversales."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class EsquemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    pagina: int
    tamano: int


class ParametrosPagina(BaseModel):
    pagina: int = Field(default=1, ge=1)
    tamano: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamano


class Problema(BaseModel):
    """Cuerpo de error conforme a RFC 7807."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
