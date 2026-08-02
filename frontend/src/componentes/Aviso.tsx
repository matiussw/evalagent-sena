import type { ReactNode } from "react";

type Tipo = "info" | "advertencia" | "error";

const CLASES: Record<Tipo, string> = {
  info: "aviso aviso--info",
  advertencia: "aviso",
  error: "aviso aviso--error",
};

export function Aviso({ tipo = "info", children }: { tipo?: Tipo; children: ReactNode }) {
  return (
    <div className={CLASES[tipo]} role={tipo === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
