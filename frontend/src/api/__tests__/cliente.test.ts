/** Tests del cliente HTTP: renovación de token y traducción de errores. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { almacenTokens, api, ErrorApi } from "../cliente";

function respuesta(estado: number, cuerpo: unknown): Response {
  return {
    ok: estado >= 200 && estado < 300,
    status: estado,
    json: async () => cuerpo,
  } as Response;
}

describe("cliente de API", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => localStorage.clear());

  it("adjunta el token de acceso en la cabecera", async () => {
    almacenTokens.guardar({
      access_token: "acceso-123",
      refresh_token: "refresco-123",
      token_type: "bearer",
      usuario: {} as never,
    });
    const fetchSimulado = vi.fn().mockResolvedValue(respuesta(200, { ok: true }));
    vi.stubGlobal("fetch", fetchSimulado);

    await api.get("/fichas");

    const [, opciones] = fetchSimulado.mock.calls[0]!;
    expect(opciones.headers.Authorization).toBe("Bearer acceso-123");
  });

  it("renueva el token y reintenta cuando el acceso caduca", async () => {
    almacenTokens.guardar({
      access_token: "caducado",
      refresh_token: "refresco-valido",
      token_type: "bearer",
      usuario: {} as never,
    });

    const fetchSimulado = vi
      .fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token caducado" }))
      .mockResolvedValueOnce(
        respuesta(200, {
          access_token: "acceso-nuevo",
          refresh_token: "refresco-nuevo",
          token_type: "bearer",
          usuario: {},
        }),
      )
      .mockResolvedValueOnce(respuesta(200, { id: "abc" }));
    vi.stubGlobal("fetch", fetchSimulado);

    const resultado = await api.get<{ id: string }>("/fichas");

    expect(resultado.id).toBe("abc");
    expect(fetchSimulado).toHaveBeenCalledTimes(3);
    expect(almacenTokens.acceso()).toBe("acceso-nuevo");
  });

  it("no entra en bucle si el refresco también falla", async () => {
    almacenTokens.guardar({
      access_token: "caducado",
      refresh_token: "refresco-invalido",
      token_type: "bearer",
      usuario: {} as never,
    });

    const fetchSimulado = vi
      .fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token caducado" }))
      .mockResolvedValueOnce(respuesta(401, { detail: "Refresco inválido" }));
    vi.stubGlobal("fetch", fetchSimulado);

    await expect(api.get("/fichas")).rejects.toThrow(ErrorApi);
    expect(fetchSimulado).toHaveBeenCalledTimes(2);
    expect(almacenTokens.acceso()).toBeNull();
  });

  it("expone el detalle RFC 7807 como mensaje para el usuario", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuesta(422, {
          type: "https://evalagent.sena.edu.co/errores/regla-de-negocio",
          title: "La operación incumple una regla de negocio",
          status: 422,
          detail: "Los pesos de los criterios deben sumar 100. Suma actual: 90.",
        }),
      ),
    );

    await expect(api.put("/guias/1/rubrica", {})).rejects.toMatchObject({
      estado: 422,
      mensajeUsuario: "Los pesos de los criterios deben sumar 100. Suma actual: 90.",
    });
  });
});
