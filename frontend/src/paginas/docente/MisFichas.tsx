import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, ErrorApi } from "@/api/cliente";
import type { Ficha } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";

export function MisFichas() {
  const cliente = useQueryClient();
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: fichas, isLoading } = useQuery({
    queryKey: ["fichas"],
    queryFn: () => api.get<Ficha[]>("/fichas"),
  });

  const crear = useMutation({
    mutationFn: (nueva: Omit<Ficha, "id" | "estado" | "docente_id">) =>
      api.post<Ficha>("/fichas", nueva),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: ["fichas"] });
      setAbierto(false);
      setError(null);
    },
    onError: (e) =>
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo crear la ficha"),
  });

  function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const datos = new FormData(evento.currentTarget);
    crear.mutate({
      codigo: String(datos.get("codigo")),
      nombre: String(datos.get("nombre")),
      programa: String(datos.get("programa")),
      trimestre: String(datos.get("trimestre")),
    });
  }

  return (
    <main className="contenedor">
      <div className="fila" style={{ justifyContent: "space-between" }}>
        <h1>Mis fichas</h1>
        <button onClick={() => setAbierto((v) => !v)}>
          {abierto ? "Cancelar" : "Nueva ficha"}
        </button>
      </div>

      {error && <Aviso tipo="error">{error}</Aviso>}

      {abierto && (
        <form className="tarjeta" onSubmit={alEnviar} style={{ marginBottom: "1.5rem" }}>
          <label htmlFor="codigo">Código de ficha</label>
          <input id="codigo" name="codigo" required placeholder="2758421" />

          <label htmlFor="nombre">Nombre</label>
          <input id="nombre" name="nombre" required placeholder="Análisis y Desarrollo de Software" />

          <label htmlFor="programa">Programa</label>
          <input id="programa" name="programa" required defaultValue="ADSO" />

          <label htmlFor="trimestre">Trimestre</label>
          <input id="trimestre" name="trimestre" required placeholder="2026-2" />

          <button type="submit" disabled={crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear ficha"}
          </button>
        </form>
      )}

      {isLoading && <p className="suave">Cargando fichas…</p>}

      {fichas?.length === 0 && (
        <Aviso>Todavía no tienes fichas. Crea la primera para empezar a publicar guías.</Aviso>
      )}

      <div className="rejilla">
        {fichas?.map((ficha) => (
          <Link
            key={ficha.id}
            to={`/docente/fichas/${ficha.id}`}
            className="tarjeta tarjeta--enlace"
          >
            <h3>{ficha.nombre}</h3>
            <p className="suave">
              Ficha {ficha.codigo} · {ficha.programa} · {ficha.trimestre}
            </p>
          </Link>
        ))}
      </div>
    </main>
  );
}
