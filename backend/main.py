import asyncio
import base64
import json
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from agent import EvaluatorAgent
from stt import transcribe_audio
from tts import synthesize_speech

app = FastAPI(title="Evaluador SENA - Agente de Sustentación")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Active sessions
sessions: dict[str, EvaluatorAgent] = {}

PROJECTS_DIR = Path(__file__).parent.parent / "proyectos"
PROJECTS_DIR.mkdir(exist_ok=True)

REPORTS_DIR = Path(__file__).parent.parent / "reportes"
REPORTS_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    return FileResponse(str(frontend_path / "index.html"))


@app.get("/api/projects")
async def list_projects():
    projects = []
    for f in PROJECTS_DIR.glob("*.md"):
        projects.append({"id": f.stem, "name": f.stem.replace("-", " ").title()})
    for f in PROJECTS_DIR.glob("*.txt"):
        projects.append({"id": f.stem, "name": f.stem.replace("-", " ").title()})
    return {"projects": projects}


@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(sessions)}


@app.get("/admin")
async def admin_page():
    return FileResponse(str(frontend_path / "admin.html"))


@app.get("/api/admin/reports")
async def list_reports():
    reports = []
    for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            reports.append({
                "id": f.stem,
                "student_name": data.get("student_name"),
                "date": data.get("date"),
                "duration": data.get("duration"),
                "percentage": data.get("percentage"),
                "approved": data.get("approved"),
                "total_score": data.get("total_score"),
                "max_score": data.get("max_score"),
                "scores": data.get("scores", {}),
            })
        except Exception:
            pass
    return {"reports": reports}


@app.get("/api/admin/reports/{report_id}")
async def get_report(report_id: str):
    path = REPORTS_DIR / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    try:
        # Init message from client
        init_data = await websocket.receive_json()
        student_name = init_data.get("student_name", "Estudiante")
        project_id = init_data.get("project_id", "")

        # Load project context
        project_context = ""
        for ext in [".md", ".txt"]:
            project_file = PROJECTS_DIR / f"{project_id}{ext}"
            if project_file.exists():
                project_context = project_file.read_text(encoding="utf-8")
                break

        if not project_context:
            project_context = "Proyecto de API REST con Node.js, Express y MongoDB. El estudiante debe sustentar sus endpoints, decisiones de diseño y manejo de errores."

        # Create agent for this session
        agent = EvaluatorAgent(student_name=student_name, project_context=project_context)
        sessions[session_id] = agent

        # Send greeting
        greeting = await agent.get_greeting()
        audio_b64 = await synthesize_speech(greeting)

        await websocket.send_json({
            "type": "agent_message",
            "text": greeting,
            "audio": audio_b64,
            "question_num": 0,
            "total_questions": agent.max_questions,
        })

        # Main conversation loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "audio_chunk":
                # Decode and transcribe audio
                audio_bytes = base64.b64decode(data["audio"])

                mime = data.get("mime_type", "audio/webm")
                ext = ".mp4" if "mp4" in mime else ".ogg" if "ogg" in mime else ".webm"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                try:
                    transcript = await transcribe_audio(tmp_path)
                finally:
                    os.unlink(tmp_path)

                if not transcript.strip():
                    await websocket.send_json({"type": "transcript_empty"})
                    continue

                # Send transcript back
                await websocket.send_json({
                    "type": "student_transcript",
                    "text": transcript,
                })

                # Get agent response
                response, is_final = await agent.respond(transcript)
                audio_b64 = await synthesize_speech(response)

                await websocket.send_json({
                    "type": "agent_message",
                    "text": response,
                    "audio": audio_b64,
                    "question_num": agent.question_count,
                    "total_questions": agent.max_questions,
                    "is_final": is_final,
                })

                if is_final:
                    scores = await agent.score_session()
                    report = agent.generate_report(scores=scores)
                    # Persist report to disk
                    report_path = REPORTS_DIR / f"{session_id}.json"
                    report_path.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    await websocket.send_json({
                        "type": "evaluation_complete",
                        "report": report,
                    })
                    break

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        sessions.pop(session_id, None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
