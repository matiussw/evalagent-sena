import { Navigate, Route, Routes } from "react-router-dom";

import { RutaProtegida } from "./componentes/RutaProtegida";
import { rutaInicial, useAuth } from "./contextos/AuthContext";
import { Login } from "./paginas/Login";
import { Registro } from "./paginas/Registro";
import { MisGuias } from "./paginas/aprendiz/MisGuias";
import { MisResultados } from "./paginas/aprendiz/MisResultados";
import { Sustentacion } from "./paginas/aprendiz/Sustentacion";
import { BandejaRevision } from "./paginas/docente/BandejaRevision";
import { DetalleFicha } from "./paginas/docente/DetalleFicha";
import { EditorGuia } from "./paginas/docente/EditorGuia";
import { MisFichas } from "./paginas/docente/MisFichas";
import { RevisarSesion } from "./paginas/docente/RevisarSesion";

export function App() {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return <p className="centrado contenedor">Cargando…</p>;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />

      <Route element={<RutaProtegida roles={["DOCENTE", "ADMIN"]} />}>
        <Route path="/docente" element={<MisFichas />} />
        <Route path="/docente/fichas/:fichaId" element={<DetalleFicha />} />
        <Route path="/docente/guias/:guiaId" element={<EditorGuia />} />
        <Route path="/docente/revision" element={<BandejaRevision />} />
        <Route path="/docente/revision/:sesionId" element={<RevisarSesion />} />
      </Route>

      <Route element={<RutaProtegida roles={["APRENDIZ"]} />}>
        <Route path="/aprendiz" element={<MisGuias />} />
        <Route path="/aprendiz/resultados" element={<MisResultados />} />
        <Route path="/sustentacion/:guiaId" element={<Sustentacion />} />
      </Route>

      <Route
        path="*"
        element={<Navigate to={usuario ? rutaInicial(usuario) : "/login"} replace />}
      />
    </Routes>
  );
}
