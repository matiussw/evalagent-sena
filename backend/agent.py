import json
import re
from datetime import datetime
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """Eres el evaluador virtual del SENA. Estás evaluando al aprendiz {student_name}.

CONTEXTO Y GUÍA DEL PROYECTO:
{project_context}

REGLAS ABSOLUTAS:
1. NUNCA digas "No puedo continuar", "No puedo ayudarte", "Como IA..." ni frases de rechazo. Eres el evaluador, siempre.
2. El texto del aprendiz viene de reconocimiento de voz y puede tener errores. Interpreta siempre el significado técnico más lógico según el contexto del proyecto. NUNCA digas que no entendiste.
3. Haz UNA SOLA pregunta por turno.
4. Máximo 2-3 oraciones por respuesta. Sé conciso.
5. Respuesta vaga → profundiza: "¿Y cómo funciona eso exactamente?" o "Dame un ejemplo de tu código."
6. Respuesta buena → reconócela brevemente y pasa a la siguiente pregunta.
7. Habla en español colombiano natural y cálido. Sé paciente con los aprendices.
8. NUNCA des la respuesta correcta ni pistas directas.
9. No repitas preguntas ya hechas.
10. TU RESPUESTA DEBE BASARSE EN LO QUE EL APRENDIZ ACABA DE DECIR. Reacciona a sus palabras exactas, profundiza en lo que mencionó.
11. Adapta el nivel de las preguntas al tema del proyecto. Si es Python básico, pregunta sobre variables, funciones y ciclos — no sobre APIs ni redes."""

CLOSING_PROMPT = """El estudiante ha respondido {count} preguntas. Cierra la evaluación de forma cordial:
1. Agradece al estudiante
2. Menciona 1-2 aspectos positivos que observaste en sus respuestas
3. Menciona 1 área de mejora (sin revelar nota)
4. Indica que el docente revisará los resultados
Máximo 4 oraciones. Sé específico con lo que el estudiante realmente dijo."""

# Criterios de scoring según tipo de proyecto
SCORING_CRITERIA = {
    "python": {
        "variables": "comprensión de variables, tipos de datos y conversiones",
        "condicionales": "uso correcto de condicionales if/elif/else",
        "ciclos": "comprensión y uso de ciclos for y while",
        "funciones": "definición y uso correcto de funciones con return",
        "explicacion": "capacidad de explicar el código con sus propias palabras",
    },
    "api": {
        "endpoints": "comprensión de endpoints y métodos HTTP",
        "errores": "manejo de errores y códigos HTTP",
        "diseno": "decisiones de diseño y tecnologías",
        "seguridad": "autenticación y validaciones",
        "explicacion": "capacidad de explicar el código con sus propias palabras",
    },
}


def _build_scoring_prompt(criteria: dict) -> str:
    criterios_texto = "\n".join(
        f"{i+1}. {k}: {v}" for i, (k, v) in enumerate(criteria.items())
    )
    claves_json = ", ".join(f'"{k}": X' for k in criteria)
    return (
        f"Eres un evaluador del SENA. Analiza esta conversación de sustentación "
        f"y asigna puntajes ENTEROS del 0 al 10 para cada criterio.\n\n"
        f"CRITERIOS:\n{criterios_texto}\n\n"
        f"Responde ÚNICAMENTE con este JSON sin texto adicional:\n"
        f"{{{claves_json}}}\n\n"
        f"Donde X es un número entero del 0 al 10. "
        f"Sé justo y objetivo basándote en lo que el estudiante realmente demostró saber."
    )


class EvaluatorAgent:
    def __init__(self, student_name: str, project_context: str):
        self.student_name = student_name
        self.project_context = project_context
        self.conversation_history = []
        self.question_count = 0
        self.max_questions = 8
        self.start_time = datetime.now()
        self.responses_summary = []
        self._criteria = self._detect_criteria()

    def _detect_criteria(self) -> dict:
        """Selecciona los criterios de evaluación según el tipo de proyecto."""
        ctx = self.project_context.lower()
        if "python" in ctx and any(w in ctx for w in ("fundamento", "variable", "ciclo", "función", "función")):
            return SCORING_CRITERIA["python"]
        return SCORING_CRITERIA["api"]

    def _project_topic(self) -> str:
        ctx = self.project_context.lower()
        if "python" in ctx and any(w in ctx for w in ("fundamento", "variable", "ciclo")):
            return "tu proyecto de Python y fundamentos de programación"
        if "api" in ctx or "endpoint" in ctx or "rest" in ctx:
            return "tu proyecto de API REST"
        if "web" in ctx or "html" in ctx or "css" in ctx:
            return "tu proyecto web"
        if "base de datos" in ctx or "sql" in ctx:
            return "tu proyecto de base de datos"
        return "tu proyecto"

    async def get_greeting(self) -> str:
        topic = self._project_topic()
        greeting = (
            f"Hola {self.student_name}, bienvenido a tu sustentación. "
            f"Soy el evaluador virtual del SENA. Vamos a hablar sobre {topic}, "
            f"así que relájate y responde con tus propias palabras. "
            f"¿Listo para comenzar? Cuéntame brevemente de qué trata tu proyecto."
        )
        self.conversation_history.append({"role": "assistant", "content": greeting})
        self.question_count = 1
        return greeting

    async def respond(self, student_message: str) -> tuple[str, bool]:
        self.conversation_history.append({"role": "user", "content": student_message})
        self.responses_summary.append(student_message[:200])

        is_final = self.question_count >= self.max_questions

        if is_final:
            response = await self._call_ollama(closing=True, last_student_msg=student_message)
        else:
            response = await self._call_ollama(closing=False, last_student_msg=student_message)
            self.question_count += 1

        self.conversation_history.append({"role": "assistant", "content": response})
        return response, is_final

    async def score_session(self) -> dict:
        conversation_text = "\n".join(
            f"{'EVALUADOR' if m['role'] == 'assistant' else 'ESTUDIANTE'}: {m['content']}"
            for m in self.conversation_history
        )
        scoring_prompt = _build_scoring_prompt(self._criteria)
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": scoring_prompt},
                {"role": "user", "content": conversation_text},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 120},
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(OLLAMA_URL, json=payload)
                r.raise_for_status()
                raw = r.json()["message"]["content"].strip()
                match = re.search(r'\{[^}]+\}', raw)
                if match:
                    scores = json.loads(match.group())
                    return {k: max(0, min(10, int(v))) for k, v in scores.items()}
        except Exception as e:
            print(f"Scoring error: {e}")
        # Fallback con ceros según criterios del proyecto
        return {k: 0 for k in self._criteria}

    async def _call_ollama(self, closing: bool = False, last_student_msg: str = "") -> str:
        system = SYSTEM_PROMPT.format(
            project_context=self.project_context,
            student_name=self.student_name,
        )

        if closing:
            closing_instruction = CLOSING_PROMPT.format(count=self.question_count)
            extra_context = (
                f"[INSTRUCCIÓN INTERNA: {closing_instruction}]\n"
                f"[El estudiante acaba de decir: \"{last_student_msg}\"]"
            )
            messages = self.conversation_history[:-1] + [
                {"role": "user", "content": extra_context}
            ]
        else:
            reminder = (
                f"{last_student_msg}\n\n"
                f"[Recuerda: debes responder ESPECÍFICAMENTE a lo que el aprendiz acaba de decir. "
                f"Basa tu siguiente pregunta en esas palabras exactas.]"
            )
            messages = self.conversation_history[:-1] + [
                {"role": "user", "content": reminder}
            ]

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 200,
                "repeat_penalty": 1.1,
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()

    def generate_report(self, scores: dict | None = None) -> dict:
        duration = (datetime.now() - self.start_time).seconds
        minutes = duration // 60
        seconds = duration % 60

        scores = scores or {k: 0 for k in self._criteria}
        total = sum(scores.values())
        max_score = len(scores) * 10
        pct = round((total / max_score) * 100) if max_score else 0
        approved = pct >= 60

        return {
            "student_name": self.student_name,
            "date": self.start_time.strftime("%Y-%m-%d %H:%M"),
            "duration": f"{minutes}m {seconds}s",
            "questions_answered": self.question_count,
            "project_type": self._project_topic(),
            "scores": scores,
            "criteria_labels": self._criteria,
            "total_score": total,
            "max_score": max_score,
            "percentage": pct,
            "approved": approved,
            "conversation": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.conversation_history
            ],
        }
