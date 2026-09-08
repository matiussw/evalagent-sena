import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorApi } from "@/api/cliente";
import { Aviso } from "@/componentes/Aviso";
import { rutaInicial, useAuth } from "@/contextos/AuthContext";

export function Registro() {
  const { registrar } = useAuth();
  const navegar = useNavigate();
  const [datos, setDatos] = useState({
    nombre: "",
    email: "",
    password: "",
    institucion_id: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function cambiar(campo: keyof typeof datos) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setDatos((previos) => ({ ...previos, [campo]: e.target.value }));
  }

  async function alEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const usuario = await registrar(datos);
      navegar(rutaInicial(usuario), { replace: true });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo crear la cuenta");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="pantalla-auth">
      <div className="caja-auth tarjeta">
        <h1>Crear cuenta de instructor</h1>

        {error && <Aviso tipo="error">{error}</Aviso>}

        <form onSubmit={alEnviar}>
          <label htmlFor="nombre">Nombre completo</label>
          <input id="nombre" value={datos.nombre} onChange={cambiar("nombre")} required autoFocus />

          <label htmlFor="email">Correo institucional</label>
          <input id="email" type="email" value={datos.email} onChange={cambiar("email")} required />

          <label htmlFor="password">Contraseña (mínimo 8 caracteres)</label>
          <input
            id="password"
            type="password"
            minLength={8}
            value={datos.password}
            onChange={cambiar("password")}
            required
            autoComplete="new-password"
          />

          <label htmlFor="institucion">Identificador de tu centro de formación</label>
          <input
            id="institucion"
            value={datos.institucion_id}
            onChange={cambiar("institucion_id")}
            required
            placeholder="Te lo facilita la coordinación académica"
          />

          <button type="submit" disabled={enviando} style={{ width: "100%" }}>
            {enviando ? "Creando…" : "Crear cuenta"}
          </button>
        </form>

        <p className="centrado suave" style={{ marginTop: "1rem" }}>
          ¿Ya tienes cuenta? <Link to="/login">Entrar</Link>
        </p>
      </div>
    </main>
  );
}
