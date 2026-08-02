import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, ErrorApi } from "@/api/cliente";
import type { RevisionConfirmada, RevisionPendiente } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";

/**
 * Pantalla de revisión: donde el instructor confirma la nota.
 *
 * Es la materialización en la interfaz del ADR-006. Todo viene precargado con
 * la propuesta del agente para que confirmar cueste poco, pero la nota no
 * existe hasta que el instructor pulsa el botón.
 */
export function RevisarSesion() {
  const { sesionId } = useParams<{ sesionId: string }>();
  const navegar = useNavigate();
  const [puntuaciones, setPuntuaciones] = useState<Record<string, number>>({});
  const [retroalimentacion, setRetroalimentacion] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: revision } = useQuery({
    queryKey: ["revision", sesionId],
    queryFn: () => api.get<RevisionPendiente>(`/sesiones/${sesionId}/revision`),
  });

  // Se parte de la propuesta del agente; el instructor ajusta lo que no comparta.
  useEffect(() => {
    if (!revision) return;
    const iniciales: Record<string, number> = {};
    for (const criterio of revision.rubrica_congelada.criterios) {
      iniciales[criterio.nombre] = revision.puntuaciones_agente?.[criterio.nombre] ?? 0;
    }
    setPuntuaciones(iniciales);
  }, [revision]);

  const confirmar = useMutation({
    mutationFn: () =>
      api.post<RevisionConfirmada>(`/sesiones/${sesionId}/revision`, {
        puntuaciones_finales: puntuaciones,
        retroalimentacion: retroalimentacion || null,
      }),
    onSuccess: () => navegar("/docente/revision"),
    onError: (e) =>
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo confirmar"),
  });

  if (!revision) return <p className="contenedor suave">Cargando sesión…</p>;

  const notaCalculada = revision.rubrica_congelada.criterios.reduce(
    (total, criterio) => total + ((puntuaciones[criterio.nombre] ?? 0) / 10) * criterio.peso,
    0,
  );
  const aprueba = notaCalculada >= revision.rubrica_congelada.umbral_aprobacion;
  const yaCalificada = revision.estado === "CALIFICADA";

  return (
    <main className="contenedor">
      <p className="suave">
        <Link to="/docente/revision">← Por revisar</Link>
      </p>
      <h1>{revision.aprendiz}</h1>
      <p className="suave">{revision.guia_titulo}</p>

      {error && <Aviso tipo="error">{error}</Aviso>}

      {yaCalificada && (
        <Aviso>Esta sesión ya fue calificada. Confirmar de nuevo actualizará la nota.</Aviso>
      )}

      {!revision.puntuaciones_agente && (
        <Aviso tipo="advertencia">
          El agente no pudo proponer una calificación para esta sesión. Puntúa a partir
          de la transcripción.
        </Aviso>
      )}

      <div className="rejilla" style={{ gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <section className="tarjeta">
          <h2>Transcripción</h2>
          <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
            {revision.turnos.map((turno) => (
              <div
                key={turno.orden}
                className={`burbuja burbuja--${turno.rol === "AGENTE" ? "agente" : "aprendiz"}`}
              >
                {turno.contenido}
              </div>
            ))}
          </div>
        </section>

        <section className="tarjeta">
          <h2>Calificación</h2>
          <p className="suave">
            {revision.puntuaciones_agente
              ? "Precargada con la propuesta del agente. Ajusta lo que no compartas."
              : "Sin propuesta previa."}
          </p>

          {revision.rubrica_congelada.criterios.map((criterio) => {
            const propuesta = revision.puntuaciones_agente?.[criterio.nombre];
            const actual = puntuaciones[criterio.nombre] ?? 0;
            const cambiado = propuesta !== undefined && propuesta !== actual;

            return (
              <div key={criterio.nombre} style={{ marginBottom: "1rem" }}>
                <label htmlFor={`c-${criterio.nombre}`}>
                  {criterio.nombre} <span className="suave">({criterio.peso} %)</span>
                  {cambiado && (
                    <span className="etiqueta etiqueta--azul" style={{ marginLeft: "0.5rem" }}>
                      agente: {propuesta}
                    </span>
                  )}
                </label>
                {criterio.descripcion && (
                  <p className="suave" style={{ fontSize: "0.85rem", margin: "0 0 0.3rem" }}>
                    {criterio.descripcion}
                  </p>
                )}
                <input
                  id={`c-${criterio.nombre}`}
                  type="range"
                  min={0}
                  max={10}
                  value={actual}
                  onChange={(e) =>
                    setPuntuaciones((previas) => ({
                      ...previas,
                      [criterio.nombre]: Number(e.target.value),
                    }))
                  }
                />
                <strong>{actual} / 10</strong>
              </div>
            );
          })}

          <label htmlFor="retro">Retroalimentación para el aprendiz</label>
          <textarea
            id="retro"
            value={retroalimentacion}
            onChange={(e) => setRetroalimentacion(e.target.value)}
            placeholder="Qué hizo bien y qué debe reforzar."
            style={{ minHeight: "100px" }}
          />

          <div className="fila" style={{ justifyContent: "space-between" }}>
            <strong style={{ fontSize: "1.3rem" }}>
              {notaCalculada.toFixed(1)} / 100{" "}
              <span className={`etiqueta etiqueta--${aprueba ? "verde" : "rojo"}`}>
                {aprueba ? "Aprueba" : "No aprueba"}
              </span>
            </strong>

            <button onClick={() => confirmar.mutate()} disabled={confirmar.isPending}>
              {confirmar.isPending ? "Confirmando…" : "Confirmar y publicar"}
            </button>
          </div>

          <p className="suave" style={{ fontSize: "0.85rem", marginTop: "0.75rem" }}>
            El aprendiz no ve ninguna nota hasta que confirmes.
          </p>
        </section>
      </div>
    </main>
  );
}
