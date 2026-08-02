import type { EstadoGuia, EstadoSesion } from "@/api/tipos";

const COLORES: Record<string, string> = {
  BORRADOR: "gris",
  PUBLICADA: "verde",
  CERRADA: "gris",
  INICIADA: "azul",
  EN_CURSO: "azul",
  PENDIENTE_REVISION: "ambar",
  CALIFICADA: "verde",
  EN_RECLAMACION: "rojo",
  ABANDONADA: "gris",
};

const TEXTOS: Record<string, string> = {
  PENDIENTE_REVISION: "Por revisar",
  EN_RECLAMACION: "En reclamación",
  EN_CURSO: "En curso",
};

export function Etiqueta({ estado }: { estado: EstadoGuia | EstadoSesion }) {
  const color = COLORES[estado] ?? "gris";
  const texto = TEXTOS[estado] ?? estado.charAt(0) + estado.slice(1).toLowerCase();

  return <span className={`etiqueta etiqueta--${color}`}>{texto}</span>;
}
