import { Navigate, Outlet } from "react-router-dom";

import type { Rol } from "@/api/tipos";
import { rutaInicial, useAuth } from "@/contextos/AuthContext";

import { Cabecera } from "./Cabecera";

/** Exige sesión iniciada y, opcionalmente, uno de los roles indicados. */
export function RutaProtegida({ roles }: { roles?: Rol[] }) {
  const { usuario, cargando } = useAuth();

  if (cargando) return <p className="centrado contenedor">Cargando…</p>;
  if (!usuario) return <Navigate to="/login" replace />;

  // Un aprendiz que llega a una ruta de docente va a su propio panel, no a un
  // error: casi siempre es un enlace guardado, no un intento de intrusión.
  if (roles && !roles.includes(usuario.rol)) {
    return <Navigate to={rutaInicial(usuario)} replace />;
  }

  return (
    <>
      <Cabecera />
      <Outlet />
    </>
  );
}
