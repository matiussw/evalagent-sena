import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/cliente";
import type { Sesion } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";
import { Etiqueta } from "@/componentes/Etiqueta";

export function BandejaRevision() {
  const { data: sesiones, isLoading } = useQuery({
    queryKey: ["sesiones", "PENDIENTE_REVISION"],
    queryFn: () => api.get<Sesion[]>("/sesiones?estado=PENDIENTE_REVISION"),
  });

  return (
    <main className="contenedor">
      <h1>Sustentaciones por revisar</h1>
      <p className="suave">
        Ninguna nota llega al aprendiz hasta que la confirmas. Revisa la transcripción,
        ajusta lo que no compartas y publica.
      </p>

      {isLoading && <p className="suave">Cargando…</p>}

      {sesiones?.length === 0 && (
        <Aviso>No hay sustentaciones pendientes. Todo al día.</Aviso>
      )}

      <div className="tabla-scroll">
        <table>
          <thead>
            <tr>
              <th>Sesión</th>
              <th>Preguntas</th>
              <th>Terminó</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {sesiones?.map((sesion) => (
              <tr key={sesion.id}>
                <td><code>{sesion.id.slice(0, 8)}</code></td>
                <td>{sesion.preguntas_respondidas}</td>
                <td>
                  {sesion.finalizada_en
                    ? new Date(sesion.finalizada_en).toLocaleString("es-CO")
                    : "—"}
                </td>
                <td><Etiqueta estado={sesion.estado} /></td>
                <td>
                  <Link className="boton" to={`/docente/revision/${sesion.id}`}>
                    Revisar
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
