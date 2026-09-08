import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorApi } from "@/api/cliente";
import { Aviso } from "@/componentes/Aviso";
import { rutaInicial, useAuth } from "@/contextos/AuthContext";

export function Login() {
  const { entrar } = useAuth();
  const navegar = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function alEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const usuario = await entrar(email, password);
      navegar(rutaInicial(usuario), { replace: true });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.mensajeUsuario : "No se pudo iniciar sesión");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="pantalla-auth">
      <div className="caja-auth tarjeta">
        <h1>EvalAgent SENA</h1>
        <p className="suave">Sustentación oral asistida por IA</p>

        {error && <Aviso tipo="error">{error}</Aviso>}

        <form onSubmit={alEnviar}>
          <label htmlFor="email">Correo institucional</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
          />

          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          <button type="submit" disabled={enviando} style={{ width: "100%" }}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <p className="centrado suave" style={{ marginTop: "1rem" }}>
          ¿Eres instructor y no tienes cuenta? <Link to="/registro">Regístrate</Link>
        </p>
      </div>
    </main>
  );
}
