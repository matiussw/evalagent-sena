import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { ProveedorAuth } from "./contextos/AuthContext";
import "./estilos/global.css";

const clienteQuery = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (intentos, error) => {
        // Un 401 o un 404 no mejoran reintentando.
        const estado = (error as { estado?: number })?.estado;
        if (estado === 401 || estado === 403 || estado === 404) return false;
        return intentos < 2;
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={clienteQuery}>
      <BrowserRouter>
        <ProveedorAuth>
          <App />
        </ProveedorAuth>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
