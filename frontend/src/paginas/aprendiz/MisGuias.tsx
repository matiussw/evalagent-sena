import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/cliente";
import type { Guia } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";

export function MisGuias() {
  const { data: guias, isLoading } = useQuery({
    queryKey: ["mis-guias"],
    queryFn: () => api.get<Guia[]>("/mis-guias"),
  });

  return (
    <main className="contenedor">
      <h1>Mis guías</h1>
      <p className="suave">
        Sustenta cuando puedas, dentro de la ventana que fijó tu instructor.
      </p>

      {isLoading && <p className="suave">Cargando…</p>}

      {guias?.length === 0 && (
        <Aviso>
          Todavía no tienes guías publicadas. Tu instructor las publicará cuando
          corresponda.
        </Aviso>
      )}

      <div className="rejilla">
        {guias?.map((guia) => (
          <div key={guia.id} className="tarjeta">
            <h3>{guia.titulo}</h3>
            {guia.descripcion && <p className="suave">{guia.descripcion}</p>}
            <p className="suave">
              {guia.num_preguntas} preguntas
              {guia.cierra_en &&
                ` · cierra el ${new Date(guia.cierra_en).toLocaleDateString("es-CO")}`}
            </p>
            <Link className="boton" to={`/sustentacion/${guia.id}`}>
              Sustentar
            </Link>
          </div>
        ))}
      </div>
    </main>
  );
}
