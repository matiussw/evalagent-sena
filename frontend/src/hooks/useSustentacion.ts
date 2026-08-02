/**
 * Sala de sustentación: captura de micrófono, canal WebSocket y reproducción.
 *
 * Reutiliza el enfoque de la v1 (MediaRecorder + turnos discretos, ver ADR-004)
 * pero lo encapsula en un hook con estado explícito, en lugar de manipular el
 * DOM directamente desde un script suelto.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import type { MensajeEntrante, MensajeSaliente } from "@/api/tipos";

export type EstadoSala =
  | "inactiva"
  | "conectando"
  | "agente_hablando"
  | "escuchando"
  | "grabando"
  | "transcribiendo"
  | "pensando"
  | "finalizada"
  | "error";

export interface Intervencion {
  rol: "AGENTE" | "APRENDIZ";
  texto: string;
}

interface Opciones {
  sesionId: string;
  ticket: string;
  totalPreguntas: number;
  alFinalizar?: (mensaje: string) => void;
}

const SEGUNDOS_LATIDO = 30;

export function useSustentacion({
  sesionId,
  ticket,
  totalPreguntas,
  alFinalizar,
}: Opciones) {
  const [estado, setEstado] = useState<EstadoSala>("inactiva");
  const [transcripcion, setTranscripcion] = useState<Intervencion[]>([]);
  const [preguntaActual, setPreguntaActual] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [avisoSinAudio, setAvisoSinAudio] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const grabadoraRef = useRef<MediaRecorder | null>(null);
  const fragmentosRef = useRef<Blob[]>([]);
  const flujoRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const enviar = useCallback((mensaje: MensajeSaliente) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(mensaje));
    }
  }, []);

  // ------------------------------------------------------------ conexión
  const conectar = useCallback(async () => {
    setEstado("conectando");
    setError(null);

    try {
      flujoRef.current = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch {
      setError(
        "No pudimos acceder a tu micrófono. Revisa los permisos del navegador y vuelve a intentarlo.",
      );
      setEstado("error");
      return;
    }

    const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocolo}//${window.location.host}/api/v1/ws/sesiones/${sesionId}?ticket=${encodeURIComponent(ticket)}`;
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onmessage = (evento) => {
      manejarMensaje(JSON.parse(evento.data) as MensajeEntrante);
    };

    socket.onerror = () => {
      setError("Se perdió la conexión con el evaluador.");
      setEstado("error");
    };

    socket.onclose = (evento) => {
      if (evento.code === 4401 || evento.code === 4403) {
        setError("Tu acceso a esta sustentación no es válido. Vuelve a iniciarla.");
        setEstado("error");
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionId, ticket]);

  const manejarMensaje = useCallback(
    (mensaje: MensajeEntrante) => {
      switch (mensaje.type) {
        case "mensaje_agente": {
          setTranscripcion((previa) => [
            ...previa,
            { rol: "AGENTE", texto: mensaje.texto },
          ]);
          setPreguntaActual(mensaje.pregunta_num);

          if (mensaje.audio) {
            reproducir(mensaje.audio, () =>
              setEstado(mensaje.es_final ? "finalizada" : "escuchando"),
            );
            setEstado("agente_hablando");
          } else {
            // El backend degrada a modo solo texto si no hay motor TTS.
            setAvisoSinAudio(true);
            setEstado(mensaje.es_final ? "finalizada" : "escuchando");
          }
          break;
        }

        case "transcripcion_aprendiz":
          setTranscripcion((previa) => [
            ...previa,
            { rol: "APRENDIZ", texto: mensaje.texto },
          ]);
          break;

        case "transcripcion_vacia":
          setError("No te escuchamos. Acércate al micrófono e inténtalo de nuevo.");
          setEstado("escuchando");
          break;

        case "estado_agente":
          setEstado(mensaje.estado === "transcribiendo" ? "transcribiendo" : "pensando");
          break;

        case "sesion_reanudada":
          setTranscripcion(
            mensaje.turnos.map((t) => ({
              rol: t.rol as "AGENTE" | "APRENDIZ",
              texto: t.contenido,
            })),
          );
          setPreguntaActual(mensaje.pregunta_num);
          setEstado("escuchando");
          break;

        case "evaluacion_completa":
          setEstado("finalizada");
          alFinalizar?.(mensaje.mensaje);
          break;

        case "error":
          setError(mensaje.mensaje);
          break;
      }
    },
    [alFinalizar],
  );

  const reproducir = (audioBase64: string, alTerminar: () => void) => {
    const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
    audioRef.current = audio;
    audio.onended = alTerminar;
    audio.onerror = alTerminar;
    void audio.play().catch(alTerminar);
  };

  // ------------------------------------------------------------ grabación
  const empezarAHablar = useCallback(() => {
    if (!flujoRef.current || estado !== "escuchando") return;

    fragmentosRef.current = [];
    const grabadora = new MediaRecorder(flujoRef.current, {
      mimeType: tipoSoportado(),
    });
    grabadoraRef.current = grabadora;

    grabadora.ondataavailable = (evento) => {
      if (evento.data.size > 0) fragmentosRef.current.push(evento.data);
    };

    grabadora.onstop = async () => {
      const blob = new Blob(fragmentosRef.current, { type: grabadora.mimeType });
      const base64 = await aBase64(blob);
      enviar({ type: "audio_chunk", audio: base64, mime_type: grabadora.mimeType });
    };

    grabadora.start();
    setError(null);
    setEstado("grabando");
  }, [estado, enviar]);

  const dejarDeHablar = useCallback(() => {
    if (grabadoraRef.current?.state === "recording") {
      grabadoraRef.current.stop();
      setEstado("transcribiendo");
    }
  }, []);

  // ------------------------------------------------------------- latido
  useEffect(() => {
    const intervalo = setInterval(() => {
      if (estado !== "inactiva" && estado !== "finalizada") {
        enviar({ type: "latido" });
      }
    }, SEGUNDOS_LATIDO * 1000);
    return () => clearInterval(intervalo);
  }, [estado, enviar]);

  // ------------------------------------------------------------ limpieza
  useEffect(
    () => () => {
      socketRef.current?.close();
      flujoRef.current?.getTracks().forEach((pista) => pista.stop());
      audioRef.current?.pause();
    },
    [],
  );

  return {
    estado,
    transcripcion,
    preguntaActual,
    totalPreguntas,
    error,
    avisoSinAudio,
    conectar,
    empezarAHablar,
    dejarDeHablar,
    finalizar: () => enviar({ type: "finalizar" }),
  };
}

/** El formato varía por navegador: Safari no soporta webm. */
function tipoSoportado(): string {
  const candidatos = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  return candidatos.find((tipo) => MediaRecorder.isTypeSupported(tipo)) ?? "";
}

function aBase64(blob: Blob): Promise<string> {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onloadend = () => {
      const resultado = lector.result as string;
      resolver(resultado.split(",")[1] ?? "");
    };
    lector.onerror = rechazar;
    lector.readAsDataURL(blob);
  });
}
