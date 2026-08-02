import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, ErrorApi } from "@/api/cliente";
import type { Ficha, Guia, Inscripcion } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";
import { Etiqueta } from "@/componentes/Etiqueta";

export function DetalleFicha() {
  const { fichaId } = useParams<{ fichaId: string }>();
  const cliente = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: ficha } = useQuery({
    queryKey: ["ficha", fichaId],
    queryFn: () => api.get<Ficha>(`/fichas/${fichaId}`),
  });

  const { data: guias } = useQuery({
    queryKey: ["guias", fichaId],
    queryFn: () => api.get<Guia[]>(`/fichas/${fichaId}/guias`),
  });

  const { data: inscripciones } = useQuery({
    queryKey: ["inscripciones", fichaId],
    queryFn: () => api.get<Inscripcion[]>(`/fichas/${fichaId}/inscripciones`),
  });

  const inscribir = useMutation({
    mutationFn: (email: string) =>
      api.post<Inscripcion>(`/fichas/${fichaId}/inscripciones`, { email }),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: ["inscripciones", fichaId] });
      setError(null);
    },
    onError: (e) =>
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo inscribir"),
  });

  const crearGuia = useMutation({
    mutationFn: (titulo: string) =>
      api.post<Guia>(`/fichas/${fichaId}/guias`, { titulo }),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["guias", fichaId] }),
  });

  return (
    <main className="contenedor">
      <p className="suave">
        <Link to="/docente">← Mis fichas</Link>
      </p>
      <h1>{ficha?.nombre ?? "Cargando…"}</h1>
      <p className="suave">
        Ficha {ficha?.codigo} · {ficha?.programa} · {ficha?.trimestre}
      </p>

      {error && <Aviso tipo="error">{error}</Aviso>}

      <section style={{ marginTop: "2rem" }}>
        <div className="fila" style={{ justifyContent: "space-between" }}>
          <h2>Guías de aprendizaje</h2>
          <button
            onClick={() => {
              const titulo = prompt("Título de la guía");
              if (titulo) crearGuia.mutate(titulo);
            }}
          >
            Nueva guía
          </button>
        </div>

        {guias?.length === 0 && (
          <Aviso>
            Sin guías todavía. Una guía define de qué preguntará el agente y con qué
            rúbrica se califica.
          </Aviso>
        )}

        <div className="rejilla">
          {guias?.map((guia) => (
            <Link
              key={guia.id}
              to={`/docente/guias/${guia.id}`}
              className="tarjeta tarjeta--enlace"
            >
              <div className="fila" style={{ justifyContent: "space-between" }}>
                <h3>{guia.titulo}</h3>
                <Etiqueta estado={guia.estado} />
              </div>
              <p className="suave">{guia.num_preguntas} preguntas</p>
            </Link>
          ))}
        </div>
      </section>

      <section style={{ marginTop: "2.5rem" }}>
        <h2>Aprendices ({inscripciones?.length ?? 0})</h2>

        <form
          className="fila"
          onSubmit={(evento) => {
            evento.preventDefault();
            const datos = new FormData(evento.currentTarget);
            inscribir.mutate(String(datos.get("email")));
            evento.currentTarget.reset();
          }}
        >
          <input
            name="email"
            type="email"
            required
            placeholder="correo@aprendiz.sena.edu.co"
            style={{ flex: 1, marginBottom: 0 }}
            aria-label="Correo del aprendiz"
          />
          <button type="submit" disabled={inscribir.isPending}>
            Inscribir
          </button>
        </form>

        <p className="suave" style={{ marginTop: "0.75rem" }}>
          Si el correo no tiene cuenta, se crea automáticamente con rol de aprendiz.
        </p>
      </section>
    </main>
  );
}
