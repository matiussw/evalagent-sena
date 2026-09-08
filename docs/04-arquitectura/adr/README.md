# Registros de decisiones de arquitectura (ADR)

Formato: **Contexto → Decisión → Alternativas → Consecuencias**.
Un ADR documenta *por qué* se eligió algo, no *cómo* funciona. Se escriben una vez y no se
reescriben: si una decisión cambia, se crea un ADR nuevo que supersede al anterior.

| ADR | Decisión | Estado | Fecha |
|---|---|---|---|
| [ADR-001](ADR-001-ejecucion-local-llm.md) | IA 100 % local, sin APIs externas | ✅ Aceptada | 2026-07-26 |
| [ADR-002](ADR-002-postgres-sobre-ficheros.md) | PostgreSQL en lugar de ficheros | ✅ Aceptada | 2026-08-02 |
| [ADR-003](ADR-003-multitenancy.md) | Multi-tenancy por columna discriminadora | ✅ Aceptada | 2026-08-02 |
| [ADR-004](ADR-004-websocket-vs-webrtc.md) | WebSocket con audio por turnos | ✅ Aceptada | 2026-07-26 |
| [ADR-005](ADR-005-tts-multiplataforma.md) | TTS como interfaz con motores intercambiables | ✅ Aceptada | 2026-08-02 |
| [ADR-006](ADR-006-humano-en-el-bucle.md) | Confirmación humana obligatoria | ✅ Aceptada | 2026-08-02 |
| [ADR-007](ADR-007-rubrica-congelada.md) | La sesión congela su rúbrica | ✅ Aceptada | 2026-08-02 |
