import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/cliente";
import type { ResultadoAprendiz } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";
import { Etiqueta } from "@/componentes/Etiqueta";

export function MisResultados() {
  const { data: resultados, isLoading } = useQuery({
    queryKey: ["mis-resultados"],
    queryFn: () => api.get<ResultadoAprendiz[]>("/mis-resultados"),
  });

  return (
    <main className="contenedor">
      <h1>Mis resultados</h1>

      {isLoading && <p className="suave">Cargando…</p>}

      {resultados?.length === 0 && (
        <Aviso>Aún no has sustentado ninguna guía.</Aviso>
      )}

      <div className="pila">
        {resultados?.map((resultado) => (
          <article key={resultado.sesion_id} className="tarjeta">
            <div className="fila" style={{ justifyContent: "space-between" }}>
              <h2>{resultado.guia_titulo}</h2>
              <Etiqueta estado={resultado.estado} />
            </div>

            {resultado.nota_final === null ? (
              // El backend no envía la propuesta del agente al aprendiz (ADR-006).
              <p className="suave">{resultado.mensaje}</p>
            ) : (
              <>
                <p style={{ fontSize: "2rem", fontWeight: 700, margin: "0.5rem 0" }}>
                  {resultado.nota_final.toFixed(1)}
                  <span className="suave" style={{ fontSize: "1rem" }}> / 100</span>{" "}
                  <span
                    className={`etiqueta etiqueta--${resultado.aprobado ? "verde" : "rojo"}`}
                  >
                    {resultado.aprobado ? "Aprobado" : "No aprobado"}
                  </span>
                </p>

                {resultado.desglose && (
                  <div className="tabla-scroll">
                    <table>
                      <thead>
                        <tr><th>Criterio</th><th>Puntuación</th></tr>
                      </thead>
                      <tbody>
                        {Object.entries(resultado.desglose).map(([criterio, puntos]) => (
                          <tr key={criterio}>
                            <td>{criterio}</td>
                            <td>{puntos} / 10</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {resultado.retroalimentacion && (
                  <>
                    <h3 style={{ marginTop: "1rem" }}>Retroalimentación de tu instructor</h3>
                    <p>{resultado.retroalimentacion}</p>
                  </>
                )}
              </>
            )}
          </article>
        ))}
      </div>
    </main>
  );
}
