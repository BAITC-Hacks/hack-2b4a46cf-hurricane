"""FastAPI application: routers, CORS, health check."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.config import settings
from src.db import engine
from src.errors import register_error_handlers
from src.llm import ask_llm
from src.schemas import AskIn, AskOut, HealthOut

# Route names become operationIds, so generated frontend types read as `ask`, not `ask_ask_post`.
app = FastAPI(
    title="App API", version="0.1.0", generate_unique_id_function=lambda route: route.name
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)


@app.get("/health", response_model=HealthOut)
async def get_health() -> HealthOut:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return HealthOut(status="ok")


@app.post("/ask", response_model=AskOut)
async def ask(payload: AskIn) -> AskOut:
    return AskOut(answer=await ask_llm(payload.prompt))
