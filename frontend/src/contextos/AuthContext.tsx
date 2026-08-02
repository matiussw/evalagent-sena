import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { almacenTokens, api, iniciarSesion } from "@/api/cliente";
import type { RespuestaTokens, Usuario } from "@/api/tipos";

interface EstadoAuth {
  usuario: Usuario | null;
  cargando: boolean;
  entrar: (email: string, password: string) => Promise<Usuario>;
  registrar: (datos: DatosRegistro) => Promise<Usuario>;
  salir: () => void;
}

export interface DatosRegistro {
  nombre: string;
  email: string;
  password: string;
  institucion_id: string;
}

const Contexto = createContext<EstadoAuth | null>(null);

export function ProveedorAuth({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  // Al recargar la página el token sigue en localStorage: se valida contra el
  // backend en lugar de confiar en él a ciegas.
  useEffect(() => {
    if (!almacenTokens.acceso()) {
      setCargando(false);
      return;
    }
    api
      .get<Usuario>("/auth/yo")
      .then(setUsuario)
      .catch(() => almacenTokens.limpiar())
      .finally(() => setCargando(false));
  }, []);

  const entrar = useCallback(async (email: string, password: string) => {
    const tokens = await iniciarSesion(email, password);
    almacenTokens.guardar(tokens);
    setUsuario(tokens.usuario);
    return tokens.usuario;
  }, []);

  const registrar = useCallback(async (datos: DatosRegistro) => {
    const tokens = await api.post<RespuestaTokens>("/auth/registro", datos);
    almacenTokens.guardar(tokens);
    setUsuario(tokens.usuario);
    return tokens.usuario;
  }, []);

  const salir = useCallback(() => {
    almacenTokens.limpiar();
    setUsuario(null);
  }, []);

  const valor = useMemo(
    () => ({ usuario, cargando, entrar, registrar, salir }),
    [usuario, cargando, entrar, registrar, salir],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth(): EstadoAuth {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useAuth debe usarse dentro de <ProveedorAuth>");
  }
  return contexto;
}

/** Ruta de inicio según el rol. */
export function rutaInicial(usuario: Usuario): string {
  switch (usuario.rol) {
    case "DOCENTE":
      return "/docente";
    case "APRENDIZ":
      return "/aprendiz";
    case "ADMIN":
      return "/docente";
  }
}
