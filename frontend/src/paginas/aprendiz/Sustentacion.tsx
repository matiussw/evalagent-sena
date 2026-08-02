import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, ErrorApi } from "@/api/cliente";
import type { GuiaDetalle, SesionIniciada } from "@/api/tipos";
import { Aviso } from "@/componentes/Aviso";
import { useSustentacion } from "@/hooks/useSustentacion";
import type { EstadoSala } from "@/hooks/useSustentacion";

const TEXTO_ESTADO: Record<EstadoSala, string> = {
  inactiva: "",
  conectando: "Conectando con el evaluador…",
  agente_hablando: "El evaluador está hablando",
  escuchando: "Tu turno: mantén pulsado para responder",
  grabando: "Grabando… suelta cuando termines",
  transcribiendo: "Transcribiendo tu respuesta…",
  pensando: "El evaluador está pensando…",
  finalizada: "Sustentación finalizada",
  error: "Hubo un problema",
};

export function Sustentacion() {
  const { guiaId } = useParams<{ guiaId: string }>();
  const [sesion, setSesion] = useState<SesionIniciada | null>(null);
  const [consentimiento, setConsentimiento] = useState(false);
  const [errorInicio, setErrorInicio] = useState<string | null>(null);
  const [mensajeFinal, setMensajeFinal] = useState<string | null>(null);

  const { data: guia } = useQuery({
    queryKey: ["guia", guiaId],
    queryFn: () => api.get<GuiaDetalle>(`/guias/${guiaId}`),
    enabled: !sesion,
  });

  const iniciar = useMutation({
    mutationFn: () =>
      api.post<SesionIniciada>("/sesiones", {
        guia_id: guiaId,
        consentimiento_aceptado: true,
      }),
    onSuccess: setSesion,
    onError: (e) =>
      setErrorInicio(
        e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo iniciar la sustentación",
      ),
  });

  if (!sesion) {
    return (
      <Preparacion
        guia={guia}
        consentimiento={consentimiento}
        setConsentimiento={setConsentimiento}
        error={errorInicio}
        iniciando={iniciar.isPending}
        alIniciar={() => iniciar.mutate()}
      />
    );
  }

  return <Sala sesion={sesion} mensajeFinal={mensajeFinal} setMensajeFinal={setMensajeFinal} />;
}

// --------------------------------------------------------------------------
// Antes de empezar: rúbrica visible y consentimiento explícito
// --------------------------------------------------------------------------

function Preparacion({
  guia,
  consentimiento,
  setConsentimiento,
  error,
  iniciando,
  alIniciar,
}: {
  guia: GuiaDetalle | undefined;
  consentimiento: boolean;
  setConsentimiento: (v: boolean) => void;
  error: string | null;
  iniciando: boolean;
  alIniciar: () => void;
}) {
  if (!guia) return <p className="contenedor suave">Cargando guía…</p>;

  return (
    <main className="contenedor" style={{ maxWidth: "720px" }}>
      <p className="suave">
        <Link to="/aprendiz">← Mis guías</Link>
      </p>
      <h1>{guia.titulo}</h1>

      {error && <Aviso tipo="error">{error}</Aviso>}

      <section className="tarjeta">
        <h2>Cómo funciona</h2>
        <ul>
          <li>Responderás <strong>{guia.num_preguntas} preguntas</strong> hablando.</li>
          <li>Mantén pulsado el botón mientras hablas y suéltalo al terminar.</li>
          <li>El evaluador repregunta según lo que digas: responde con tus palabras.</li>
          <li>
            Al terminar, <strong>tu instructor revisa</strong> la sustentación y publica
            la nota. El sistema no califica solo.
          </li>
        </ul>
      </section>

      {guia.rubrica && (
        <section className="tarjeta" style={{ marginTop: "1rem" }}>
          <h2>Con qué te van a evaluar</h2>
          <div className="tabla-scroll">
            <table>
              <thead>
                <tr><th>Criterio</th><th>Peso</th></tr>
              </thead>
              <tbody>
                {guia.rubrica.criterios.map((criterio) => (
                  <tr key={criterio.id}>
                    <td>
                      <strong>{criterio.nombre}</strong>
                      {criterio.descripcion && (
                        <div className="suave">{criterio.descripcion}</div>
                      )}
                    </td>
                    <td>{criterio.peso} %</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="suave">
            Se aprueba con {guia.rubrica.umbral_aprobacion} % o más.
          </p>
        </section>
      )}

      <section className="tarjeta" style={{ marginTop: "1rem" }}>
        <h2>Tratamiento de tus datos</h2>
        <p className="suave">
          Se guarda la <strong>transcripción</strong> de lo que digas, no el audio. Todo
          el procesamiento ocurre en los servidores de tu centro de formación: nada se
          envía a servicios externos. Tu instructor y la coordinación académica podrán
          consultar la transcripción como evidencia de la evaluación.
        </p>

        <label className="fila" style={{ fontWeight: 400 }}>
          <input
            type="checkbox"
            checked={consentimiento}
            onChange={(e) => setConsentimiento(e.target.checked)}
            style={{ width: "auto", marginBottom: 0 }}
          />
          Acepto el tratamiento de mis datos para esta evaluación.
        </label>

        <button onClick={alIniciar} disabled={!consentimiento || iniciando}>
          {iniciando ? "Preparando…" : "Iniciar sustentación"}
        </button>
      </section>
    </main>
  );
}

// --------------------------------------------------------------------------
// La sala
// --------------------------------------------------------------------------

function Sala({
  sesion,
  mensajeFinal,
  setMensajeFinal,
}: {
  sesion: SesionIniciada;
  mensajeFinal: string | null;
  setMensajeFinal: (m: string) => void;
}) {
  const finalRef = useRef<HTMLDivElement>(null);
  const {
    estado,
    transcripcion,
    preguntaActual,
    totalPreguntas,
    error,
    avisoSinAudio,
    conectar,
    empezarAHablar,
    dejarDeHablar,
  } = useSustentacion({
    sesionId: sesion.id,
    ticket: sesion.ws_ticket,
    totalPreguntas: sesion.num_preguntas,
    alFinalizar: setMensajeFinal,
  });

  // El ticket del WebSocket caduca en 60 s: hay que conectar de inmediato.
  useEffect(() => {
    void conectar();
  }, [conectar]);

  useEffect(() => {
    finalRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripcion]);

  const puedeHablar = estado === "escuchando" || estado === "grabando";
  const progreso = totalPreguntas
    ? Math.round((preguntaActual / totalPreguntas) * 100)
    : 0;

  if (mensajeFinal) {
    return (
      <main className="sala centrado">
        <h1>Sustentación completada</h1>
        <Aviso tipo="info">{mensajeFinal}</Aviso>
        <Link className="boton" to="/aprendiz/resultados">
          Ver mis resultados
        </Link>
      </main>
    );
  }

  return (
    <main className="sala">
      <h1>{sesion.guia_titulo}</h1>

      <div
        className="sala__progreso"
        role="progressbar"
        aria-valuenow={preguntaActual}
        aria-valuemin={0}
        aria-valuemax={totalPreguntas}
        aria-label="Progreso de la sustentación"
      >
        <div style={{ width: `${progreso}%` }} />
      </div>
      <p className="sala__estado" aria-live="polite">
        {TEXTO_ESTADO[estado]}
        {preguntaActual > 0 && ` · pregunta ${preguntaActual} de ${totalPreguntas}`}
      </p>

      {avisoSinAudio && (
        <Aviso tipo="advertencia">
          El evaluador no tiene voz disponible en este servidor. Puedes seguir la
          sustentación por texto con normalidad.
        </Aviso>
      )}

      {error && <Aviso tipo="error">{error}</Aviso>}

      <section aria-label="Conversación" style={{ marginTop: "1.5rem" }}>
        {transcripcion.map((intervencion, indice) => (
          <div
            key={indice}
            className={`burbuja burbuja--${intervencion.rol === "AGENTE" ? "agente" : "aprendiz"}`}
          >
            {intervencion.texto}
          </div>
        ))}
        <div ref={finalRef} />
      </section>

      {estado !== "finalizada" && (
        <button
          className={`microfono ${estado === "grabando" ? "microfono--grabando" : ""}`}
          disabled={!puedeHablar}
          onMouseDown={empezarAHablar}
          onMouseUp={dejarDeHablar}
          onMouseLeave={dejarDeHablar}
          onTouchStart={(e) => {
            e.preventDefault();
            empezarAHablar();
          }}
          onTouchEnd={(e) => {
            e.preventDefault();
            dejarDeHablar();
          }}
        >
          {estado === "grabando" ? "Suelta para enviar" : "Mantén pulsado para hablar"}
        </button>
      )}
    </main>
  );
}
