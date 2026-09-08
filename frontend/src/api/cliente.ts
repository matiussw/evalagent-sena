/**
 * Cliente HTTP de la API.
 *
 * Renueva el token de acceso de forma transparente cuando caduca: ante un 401
 * intenta el refresco una sola vez y reintenta la petición original. Sin esto,
 * una sustentación de 15 minutos se cortaría al expirar el token de 30.
 */

import type { Problema, RespuestaTokens } from "./tipos";

const BASE = "/api/v1";

const CLAVE_ACCESO = "evalagent.access";
const CLAVE_REFRESCO = "evalagent.refresh";

export const almacenTokens = {
  acceso: () => localStorage.getItem(CLAVE_ACCESO),
  refresco: () => localStorage.getItem(CLAVE_REFRESCO),
  guardar(tokens: RespuestaTokens) {
    localStorage.setItem(CLAVE_ACCESO, tokens.access_token);
    localStorage.setItem(CLAVE_REFRESCO, tokens.refresh_token);
  },
  limpiar() {
    localStorage.removeItem(CLAVE_ACCESO);
    localStorage.removeItem(CLAVE_REFRESCO);
  },
};

export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    readonly problema: Problema | null,
    mensaje: string,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }

  /** Mensaje pensado para mostrar al usuario. */
  get mensajeUsuario(): string {
    return this.problema?.detail ?? this.problema?.title ?? this.message;
  }
}

interface Opciones extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Interno: evita bucles de refresco. */
  _reintentado?: boolean;
}

async function refrescarTokens(): Promise<boolean> {
  const refresco = almacenTokens.refresco();
  if (!refresco) return false;

  const respuesta = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresco }),
  });

  if (!respuesta.ok) {
    almacenTokens.limpiar();
    return false;
  }

  almacenTokens.guardar((await respuesta.json()) as RespuestaTokens);
  return true;
}

export async function peticion<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const { body, headers, _reintentado, ...resto } = opciones;
  const acceso = almacenTokens.acceso();

  const respuesta = await fetch(`${BASE}${ruta}`, {
    ...resto,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(acceso ? { Authorization: `Bearer ${acceso}` } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (respuesta.status === 401 && !_reintentado && almacenTokens.refresco()) {
    if (await refrescarTokens()) {
      return peticion<T>(ruta, { ...opciones, _reintentado: true });
    }
  }

  if (!respuesta.ok) {
    const problema = await respuesta.json().catch(() => null);
    throw new ErrorApi(
      respuesta.status,
      problema,
      problema?.detail ?? `Error ${respuesta.status}`,
    );
  }

  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}

export const api = {
  get: <T,>(ruta: string) => peticion<T>(ruta),
  post: <T,>(ruta: string, body?: unknown) => peticion<T>(ruta, { method: "POST", body }),
  patch: <T,>(ruta: string, body: unknown) => peticion<T>(ruta, { method: "PATCH", body }),
  put: <T,>(ruta: string, body: unknown) => peticion<T>(ruta, { method: "PUT", body }),
  delete: <T,>(ruta: string) => peticion<T>(ruta, { method: "DELETE" }),
};

/** Login: el backend espera `application/x-www-form-urlencoded` (OAuth2). */
export async function iniciarSesion(
  email: string,
  password: string,
): Promise<RespuestaTokens> {
  const cuerpo = new URLSearchParams({ username: email, password });
  const respuesta = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: cuerpo,
  });

  if (!respuesta.ok) {
    const problema = await respuesta.json().catch(() => null);
    throw new ErrorApi(
      respuesta.status,
      problema,
      problema?.detail ?? "No se pudo iniciar sesión",
    );
  }

  return (await respuesta.json()) as RespuestaTokens;
}
