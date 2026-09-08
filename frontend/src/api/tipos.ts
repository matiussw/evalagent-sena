/** Tipos del dominio, espejo de los esquemas Pydantic del backend. */

export type Rol = "ADMIN" | "DOCENTE" | "APRENDIZ";

export type EstadoFicha = "ACTIVA" | "ARCHIVADA";
export type EstadoGuia = "BORRADOR" | "PUBLICADA" | "CERRADA";

export type EstadoSesion =
  | "INICIADA"
  | "EN_CURSO"
  | "PENDIENTE_REVISION"
  | "CALIFICADA"
  | "EN_RECLAMACION"
  | "ABANDONADA";

export interface Usuario {
  id: string;
  nombre: string;
  email: string;
  rol: Rol;
  institucion_id: string;
}

export interface RespuestaTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  usuario: Usuario;
}

export interface Ficha {
  id: string;
  codigo: string;
  nombre: string;
  programa: string;
  trimestre: string;
  estado: EstadoFicha;
  docente_id: string;
}

export interface Guia {
  id: string;
  ficha_id: string;
  titulo: string;
  descripcion: string | null;
  num_preguntas: number;
  estado: EstadoGuia;
  abre_en: string | null;
  cierra_en: string | null;
}

export interface GuiaDetalle extends Guia {
  contexto_tecnico: string | null;
  rubrica: Rubrica | null;
}

export interface Criterio {
  id: string;
  nombre: string;
  descripcion: string | null;
  peso: number;
  orden: number;
}

export interface Rubrica {
  id: string;
  guia_id: string;
  umbral_aprobacion: number;
  criterios: Criterio[];
}

/** Rúbrica congelada en una sesión (ADR-007): sin ids, es una copia JSON. */
export interface RubricaCongelada {
  version_esquema: number;
  umbral_aprobacion: number;
  criterios: { nombre: string; descripcion: string | null; peso: number }[];
}

export interface Inscripcion {
  id: string;
  ficha_id: string;
  aprendiz_id: string;
  estado: "ACTIVA" | "RETIRADA";
}

export interface Turno {
  orden: number;
  rol: "AGENTE" | "APRENDIZ";
  contenido: string;
  creado_en: string;
}

export interface SesionIniciada {
  id: string;
  estado: EstadoSesion;
  guia_titulo: string;
  num_preguntas: number;
  rubrica_congelada: RubricaCongelada;
  ws_ticket: string;
  ws_url: string;
}

export interface Sesion {
  id: string;
  guia_id: string;
  aprendiz_id: string;
  estado: EstadoSesion;
  preguntas_respondidas: number;
  iniciada_en: string | null;
  finalizada_en: string | null;
}

export interface RevisionPendiente {
  sesion_id: string;
  aprendiz: string;
  guia_titulo: string;
  estado: EstadoSesion;
  rubrica_congelada: RubricaCongelada;
  puntuaciones_agente: Record<string, number> | null;
  nota_propuesta: number | null;
  turnos: Turno[];
}

export interface RevisionConfirmada {
  sesion_id: string;
  estado: EstadoSesion;
  nota_final: number;
  aprobado: boolean;
  revisor_id: string;
  confirmada_en: string;
  diferencias_con_agente: Record<string, { agente: number; final: number }>;
}

/**
 * Resultado visible para el aprendiz.
 *
 * Mientras la sesión no esté CALIFICADA, `nota_final` y `desglose` llegan a
 * `null` y solo se recibe `mensaje` — el backend nunca envía la propuesta del
 * agente al aprendiz (ADR-006).
 */
export interface ResultadoAprendiz {
  sesion_id: string;
  guia_titulo: string;
  estado: EstadoSesion;
  mensaje: string | null;
  nota_final: number | null;
  aprobado: boolean | null;
  desglose: Record<string, number> | null;
  retroalimentacion: string | null;
}

/** Cuerpo de error del backend, conforme a RFC 7807. */
export interface Problema {
  type: string;
  title: string;
  status: number;
  detail: string | null;
  instance: string | null;
}

// --------------------------------------------------------------------------
// Mensajes del canal WebSocket
// --------------------------------------------------------------------------

export type MensajeEntrante =
  | {
      type: "mensaje_agente";
      texto: string;
      audio: string;
      pregunta_num: number;
      total_preguntas: number;
      es_final: boolean;
      latencia_ms?: number;
    }
  | { type: "transcripcion_aprendiz"; texto: string }
  | { type: "transcripcion_vacia" }
  | { type: "estado_agente"; estado: "transcribiendo" | "pensando" | "hablando" }
  | {
      type: "sesion_reanudada";
      pregunta_num: number;
      total_preguntas: number;
      turnos: { rol: string; contenido: string }[];
    }
  | { type: "evaluacion_completa"; sesion_id: string; estado: EstadoSesion; mensaje: string }
  | { type: "error"; codigo: string; mensaje: string };

export type MensajeSaliente =
  | { type: "audio_chunk"; audio: string; mime_type: string }
  | { type: "latido" }
  | { type: "finalizar" };
