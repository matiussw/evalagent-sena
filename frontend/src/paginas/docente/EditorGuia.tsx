import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api, ErrorApi } from "@/api/cliente";
import type { GuiaDetalle } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";
import { Etiqueta } from "@/componentes/Etiqueta";

interface CriterioEditable {
  nombre: string;
  descripcion: string;
  peso: number;
}

const PLANTILLAS: Record<string, CriterioEditable[]> = {
  "API REST": [
    { nombre: "Endpoints", descripcion: "Comprensión de endpoints y verbos HTTP", peso: 25 },
    { nombre: "Manejo de errores", descripcion: "Códigos de estado y validaciones", peso: 20 },
    { nombre: "Diseño", descripcion: "Decisiones de arquitectura y tecnología", peso: 20 },
    { nombre: "Seguridad", descripcion: "Autenticación y control de acceso", peso: 15 },
    { nombre: "Explicación", descripcion: "Claridad al explicar su propio código", peso: 20 },
  ],
  "Fundamentos de Python": [
    { nombre: "Variables", descripcion: "Tipos de datos y conversiones", peso: 20 },
    { nombre: "Condicionales", descripcion: "Uso correcto de if/elif/else", peso: 20 },
    { nombre: "Ciclos", descripcion: "Comprensión de for y while", peso: 20 },
    { nombre: "Funciones", descripcion: "Definición, parámetros y return", peso: 20 },
    { nombre: "Explicación", descripcion: "Claridad al explicar su propio código", peso: 20 },
  ],
};

export function EditorGuia() {
  const { guiaId } = useParams<{ guiaId: string }>();
  const cliente = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [criterios, setCriterios] = useState<CriterioEditable[]>([]);
  const [umbral, setUmbral] = useState(60);

  const { data: guia } = useQuery({
    queryKey: ["guia", guiaId],
    queryFn: () => api.get<GuiaDetalle>(`/guias/${guiaId}`),
  });

  useEffect(() => {
    if (guia?.rubrica) {
      setCriterios(
        guia.rubrica.criterios.map((c) => ({
          nombre: c.nombre,
          descripcion: c.descripcion ?? "",
          peso: c.peso,
        })),
      );
      setUmbral(guia.rubrica.umbral_aprobacion);
    }
  }, [guia]);

  const sumaPesos = criterios.reduce((total, c) => total + c.peso, 0);

  const guardarGuia = useMutation({
    mutationFn: (cambios: Partial<GuiaDetalle>) => api.patch(`/guias/${guiaId}`, cambios),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["guia", guiaId] }),
    onError: (e) => setError(e instanceof ErrorApi ? e.mensajeUsuario : "Error al guardar"),
  });

  const guardarRubrica = useMutation({
    mutationFn: () =>
      api.put(`/guias/${guiaId}/rubrica`, {
        umbral_aprobacion: umbral,
        criterios: criterios.map((c) => ({
          nombre: c.nombre,
          descripcion: c.descripcion || null,
          peso: c.peso,
        })),
      }),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: ["guia", guiaId] });
      setError(null);
    },
    onError: (e) =>
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "Error al guardar la rúbrica"),
  });

  const publicar = useMutation({
    mutationFn: () => api.post(`/guias/${guiaId}/publicar`),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: ["guia", guiaId] });
      setError(null);
    },
    onError: (e) =>
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo publicar"),
  });

  if (!guia) return <p className="contenedor suave">Cargando guía…</p>;

  return (
    <main className="contenedor">
      <div className="fila" style={{ justifyContent: "space-between" }}>
        <h1>{guia.titulo}</h1>
        <Etiqueta estado={guia.estado} />
      </div>

      {error && <Aviso tipo="error">{error}</Aviso>}

      <section className="tarjeta" style={{ marginTop: "1.5rem" }}>
        <h2>Contexto técnico</h2>
        <p className="suave">
          Es lo que el agente usa para formular las preguntas. Cuanto más concreto,
          mejores preguntas: enumera temas, endpoints y decisiones que el aprendiz debe
          saber explicar.
        </p>

        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            const datos = new FormData(evento.currentTarget);
            guardarGuia.mutate({
              contexto_tecnico: String(datos.get("contexto")),
              num_preguntas: Number(datos.get("preguntas")),
              abre_en: new Date(String(datos.get("abre"))).toISOString(),
              cierra_en: new Date(String(datos.get("cierra"))).toISOString(),
            });
          }}
        >
          <textarea
            name="contexto"
            defaultValue={guia.contexto_tecnico ?? ""}
            placeholder={"## Temas evaluables\n- Endpoints y verbos HTTP\n- Códigos de estado"}
            aria-label="Contexto técnico"
          />

          <div className="rejilla">
            <div>
              <label htmlFor="preguntas">Número de preguntas</label>
              <input
                id="preguntas"
                name="preguntas"
                type="number"
                min={3}
                max={20}
                defaultValue={guia.num_preguntas}
              />
            </div>
            <div>
              <label htmlFor="abre">Abre</label>
              <input
                id="abre"
                name="abre"
                type="datetime-local"
                defaultValue={aLocal(guia.abre_en)}
                required
              />
            </div>
            <div>
              <label htmlFor="cierra">Cierra</label>
              <input
                id="cierra"
                name="cierra"
                type="datetime-local"
                defaultValue={aLocal(guia.cierra_en)}
                required
              />
            </div>
          </div>

          <button type="submit" disabled={guardarGuia.isPending}>
            Guardar guía
          </button>
        </form>
      </section>

      <section className="tarjeta" style={{ marginTop: "1.5rem" }}>
        <h2>Rúbrica</h2>
        <p className="suave">
          Tus criterios, aplicados igual a todos tus aprendices. Los pesos deben sumar 100.
        </p>

        <div className="fila">
          {Object.entries(PLANTILLAS).map(([nombre, plantilla]) => (
            <button
              key={nombre}
              type="button"
              className="secundario"
              onClick={() => setCriterios(plantilla.map((c) => ({ ...c })))}
            >
              Usar plantilla «{nombre}»
            </button>
          ))}
        </div>

        <div className="tabla-scroll" style={{ marginTop: "1rem" }}>
          <table>
            <thead>
              <tr>
                <th>Criterio</th>
                <th>Descripción</th>
                <th style={{ width: "6rem" }}>Peso %</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {criterios.map((criterio, indice) => (
                <tr key={indice}>
                  <td>
                    <input
                      value={criterio.nombre}
                      onChange={(e) => actualizar(indice, { nombre: e.target.value })}
                      style={{ marginBottom: 0 }}
                      aria-label={`Nombre del criterio ${indice + 1}`}
                    />
                  </td>
                  <td>
                    <input
                      value={criterio.descripcion}
                      onChange={(e) => actualizar(indice, { descripcion: e.target.value })}
                      style={{ marginBottom: 0 }}
                      aria-label={`Descripción del criterio ${indice + 1}`}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={criterio.peso}
                      onChange={(e) => actualizar(indice, { peso: Number(e.target.value) })}
                      style={{ marginBottom: 0 }}
                      aria-label={`Peso del criterio ${indice + 1}`}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="secundario"
                      onClick={() =>
                        setCriterios((previos) => previos.filter((_, i) => i !== indice))
                      }
                      aria-label={`Eliminar criterio ${indice + 1}`}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="fila" style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="secundario"
            onClick={() =>
              setCriterios((previos) => [
                ...previos,
                { nombre: "", descripcion: "", peso: 0 },
              ])
            }
          >
            Añadir criterio
          </button>

          <span className={sumaPesos === 100 ? "etiqueta etiqueta--verde" : "etiqueta etiqueta--rojo"}>
            Suma: {sumaPesos} %
          </span>

          <label htmlFor="umbral" style={{ marginBottom: 0 }}>
            Umbral de aprobación
          </label>
          <input
            id="umbral"
            type="number"
            min={0}
            max={100}
            value={umbral}
            onChange={(e) => setUmbral(Number(e.target.value))}
            style={{ width: "5rem", marginBottom: 0 }}
          />

          <button
            type="button"
            onClick={() => guardarRubrica.mutate()}
            disabled={sumaPesos !== 100 || guardarRubrica.isPending}
          >
            Guardar rúbrica
          </button>
        </div>
      </section>

      {guia.estado === "BORRADOR" && (
        <section className="tarjeta" style={{ marginTop: "1.5rem" }}>
          <h2>Publicar</h2>
          <p className="suave">
            Al publicar, tus aprendices inscritos podrán sustentar dentro de la ventana
            indicada. Hace falta contexto técnico, rúbrica y fechas.
          </p>
          <button onClick={() => publicar.mutate()} disabled={publicar.isPending}>
            {publicar.isPending ? "Publicando…" : "Publicar guía"}
          </button>
        </section>
      )}
    </main>
  );

  function actualizar(indice: number, cambios: Partial<CriterioEditable>) {
    setCriterios((previos) =>
      previos.map((c, i) => (i === indice ? { ...c, ...cambios } : c)),
    );
  }
}

/** `datetime-local` no acepta ISO con zona horaria. */
function aLocal(iso: string | null): string {
  if (!iso) return "";
  const fecha = new Date(iso);
  const desfase = fecha.getTimezoneOffset() * 60_000;
  return new Date(fecha.getTime() - desfase).toISOString().slice(0, 16);
}
