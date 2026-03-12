"""
api/main.py
-----------
API FastAPI que serve a página web e expõe endpoints REST
para execução do AG e consulta de resultados.

Endpoints:
    GET  /                      → página principal (HTML)
    POST /otimizar              → inicia o AG em background
    GET  /status/{job_id}       → status e progresso do job
    GET  /resultado/{job_id}    → resultado completo (rotas + LLM)
    GET  /jobs                  → lista todos os jobs
    DELETE /jobs/{job_id}       → cancela job em andamento
    GET  /health                → healthcheck

Uso:
    pip install fastapi uvicorn
    uvicorn api.main:app --reload --port 8000
"""

import uuid
import threading
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.runner import run_ag
from generate_test_report import (
    run_tests, build_test_context, build_test_prompt,
    call_openai, load_api_key,
)

# Job de testes (separado dos jobs do AG)
TEST_JOBS: Dict[str, Dict[str, Any]] = {}


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="VRP Hospitalar — RMSP",
    description="Otimização de rotas de distribuição de medicamentos via Algoritmo Genético",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve arquivos estáticos (CSS, JS)
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Armazenamento em memória dos jobs
JOBS: Dict[str, Dict[str, Any]] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class VehicleConfig(BaseModel):
    id:           int   = Field(..., example=1)
    capacity:     int   = Field(150, example=150)
    max_distance: float = Field(5.0, example=5.0, description="Autonomia em graus lat/lon")


class OtimizarRequest(BaseModel):
    population_size: int            = Field(100,   ge=20,  le=500)
    stagnation_stop: int            = Field(400,   ge=50,  le=2000)
    mutation_start:  float          = Field(0.30,  ge=0.05, le=0.90)
    depot:           str            = Field("Barueri")
    vehicles:        List[VehicleConfig] = Field(default_factory=lambda: [
        VehicleConfig(id=1, capacity=150, max_distance=5.0),
        VehicleConfig(id=2, capacity=150, max_distance=5.0),
        VehicleConfig(id=3, capacity=500, max_distance=8.0),
    ])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a página principal."""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "jobs_ativos": sum(1 for j in JOBS.values() if j["status"] == "running")}


@app.post("/otimizar")
async def otimizar(req: OtimizarRequest):
    """Inicia o AG em background e retorna job_id para acompanhamento."""
    job_id = str(uuid.uuid4())[:8]

    job = {
        "id":           job_id,
        "status":       "pending",
        "progress":     0,
        "generation":   0,
        "best_fitness": None,
        "current_km":   None,
        "sem_melhoria": 0,
        "cancel":       False,
        "routes":       None,
        "llm_report":   None,
        "fitness_history": [],
        "km_history":      [],
    }
    JOBS[job_id] = job

    config = {
        "population_size": req.population_size,
        "stagnation_stop": req.stagnation_stop,
        "mutation_start":  req.mutation_start,
        "mutation_min":    0.05,
        "elite_size":      5,
        "tournament_size": 3,
        "depot":           req.depot,
        "vehicles":        [v.dict() for v in req.vehicles],
    }

    thread = threading.Thread(target=run_ag, args=(config, job), daemon=True)
    thread.start()

    return {"job_id": job_id, "message": "AG iniciado. Acompanhe via /status/" + job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    """Retorna progresso atual do job (polling da página web)."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = JOBS[job_id]
    return {
        "job_id":       job_id,
        "status":       job["status"],
        "progress":     job["progress"],
        "generation":   job["generation"],
        "best_fitness": job["best_fitness"],
        "current_km":   job["current_km"],
        "sem_melhoria": job["sem_melhoria"],
        # histórico comprimido: envia apenas os últimos 200 pontos para o gráfico
        "fitness_history": job["fitness_history"][-200:],
        "km_history":      job["km_history"][-200:],
    }


@app.get("/resultado/{job_id}")
async def resultado(job_id: str):
    """Retorna resultado completo: rotas, KM, relatório LLM."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = JOBS[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=202, detail=f"Job ainda em execução: {job['status']}")

    return {
        "job_id":           job_id,
        "status":           "done",
        "generation":       job["generation"],
        "best_fitness":     job["best_fitness"],
        "total_km":         job["total_km"],
        "best_km":          job.get("best_km", job["total_km"]),
        "routes":           job["routes"],
        "depot":            job["depot"],
        "fitness_history":  job["fitness_history"],
        "km_history":       job["km_history"],
        "best_global_hist": job.get("best_global_hist", []),
        "best_km_history":  job.get("best_km_history", []),
        "llm_report":       job["llm_report"],
    }


@app.get("/jobs")
async def list_jobs():
    """Lista todos os jobs com seus status."""
    return [
        {
            "job_id":     jid,
            "status":     j["status"],
            "progress":   j["progress"],
            "generation": j["generation"],
        }
        for jid, j in JOBS.items()
    ]



# ── Endpoints de Testes ───────────────────────────────────────────────────────

@app.post("/testes/executar")
async def executar_testes():
    """Executa os testes automatizados em background e retorna job_id."""
    import uuid, threading

    job_id = "test-" + str(uuid.uuid4())[:6]
    job = {
        "id":      job_id,
        "status":  "running",
        "context": None,
        "report":  None,
        "error":   None,
        "stats":   None,
    }
    TEST_JOBS[job_id] = job

    def _run():
        try:
            result  = run_tests()
            context = build_test_context(result)

            passou  = result.testsRun - len(result.failures) - len(result.errors)
            job["stats"] = {
                "total":   result.testsRun,
                "passou":  passou,
                "falhou":  len(result.failures),
                "erros":   len(result.errors),
                "taxa":    round(passou / result.testsRun * 100, 1) if result.testsRun else 0,
            }
            job["context"] = context

            api_key = load_api_key()
            if api_key:
                prompt = build_test_prompt(context)
                job["report"] = call_openai(prompt, api_key)
            else:
                job["report"] = (
                    "⚠ OPENAI_API_KEY não configurada.\n"
                    "Configure em .env para gerar o relatório com LLM.\n\n"
                    + context
                )

            job["status"] = "done"
        except Exception as e:
            job["status"] = "error"
            job["error"]  = str(e)

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id}


@app.get("/testes/status/{job_id}")
async def status_testes(job_id: str):
    """Retorna status do job de testes."""
    if job_id not in TEST_JOBS:
        raise HTTPException(status_code=404, detail="Job de testes não encontrado")
    job = TEST_JOBS[job_id]
    return {
        "job_id":  job_id,
        "status":  job["status"],
        "stats":   job["stats"],
        "report":  job["report"],
        "error":   job["error"],
    }

@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancela um job em andamento."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    JOBS[job_id]["cancel"] = True
    return {"message": f"Job {job_id} marcado para cancelamento"}
