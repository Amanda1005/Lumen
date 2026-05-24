import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Path as PathParam, Query
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

# Rate limiter (60 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Lumen API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - only allow your frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    # Add production domain later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],  # Only GET endpoints for now
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).parent.parent / "data" / "agents_with_comments.json"


def load_agents() -> list[dict]:
    if not DATA_PATH.exists():
        raise HTTPException(500, "Data not found. Run pipeline.py first.")
    with open(DATA_PATH) as f:
        return json.load(f)


@app.get("/")
@limiter.limit("60/minute")
def root(request: Request):
    return {"name": "Lumen API", "status": "ok"}


@app.get("/api/stats")
@limiter.limit("60/minute")
def stats(request: Request):
    agents = load_agents()
    return {
        "total_agents": len(agents),
        "safe": sum(1 for a in agents if a.get("risk_level") == "SAFE"),
        "sybil": sum(1 for a in agents if a.get("risk_level") == "SYBIL"),
        "avg_score": round(sum(a["lumen_score"] for a in agents) / len(agents), 1),
    }


@app.get("/api/agents")
@limiter.limit("60/minute")
def list_agents(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    risk: str | None = Query(None, pattern="^(SAFE|SUSPICIOUS|SYBIL)$"),
):
    agents = load_agents()
    if risk:
        agents = [a for a in agents if a.get("risk_level") == risk.upper()]
    return {
        "count": len(agents),
        "agents": [
            {
                "agent_id": a["agent_id"],
                "name": a.get("name", "(unnamed)"),
                "owner": a["owner"],
                "lumen_score": a["lumen_score"],
                "grade": a["grade"],
                "risk_level": a.get("risk_level"),
                "breakdown": a["breakdown"],
            }
            for a in agents[:limit]
        ],
    }


@app.get("/api/agents/{agent_id}")
@limiter.limit("60/minute")
def get_agent(
    request: Request,
    agent_id: int = PathParam(..., ge=0, le=100000),
):
    agents = load_agents()
    for a in agents:
        if a["agent_id"] == agent_id:
            return a
    raise HTTPException(404, f"Agent {agent_id} not found")