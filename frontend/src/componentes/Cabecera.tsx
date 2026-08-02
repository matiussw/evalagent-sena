import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "@/contextos/AuthContext";

export function Cabecera() {
  const { usuario, salir } = useAuth();
  const navegar = useNavigate();

  if (!usuario) return null;

  const esDocente = usuario.rol === "DOCENTE" || usuario.rol === "ADMIN";

  return (
    <header className="barra">
      <Link to="/" className="marca">
        EvalAgent SENA
      </Link>

      <nav>
        {esDocente ? (
          <>
            <Link to="/docente">Mis fichas</Link>
            <Link to="/docente/revision">Por revisar</Link>
          </>
        ) : (
          <>
            <Link to="/aprendiz">Mis guías</Link>
            <Link to="/aprendiz/resultados">Mis resultados</Link>
          </>
        )}
      </nav>

      <div className="fila">
        <span className="suave">{usuario.nombre}</span>
        <button
          className="secundario"
          onClick={() => {
            salir();
            navegar("/login");
          }}
        >
          Salir
        </button>
      </div>
    </header>
  );
}
