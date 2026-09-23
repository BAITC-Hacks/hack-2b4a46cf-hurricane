"""FastAPI application: routers, CORS, health check."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src import catalog, recommend
from src.config import settings
from src.db import engine
from src.errors import register_error_handlers
from src.schemas import HealthOut

# Route names become operationIds: generated types read `recommend`, not `recommend_recommend_post`.
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
app.include_router(catalog.router)
app.include_router(recommend.router)


# Infra-only: Docker and Railway healthchecks poll it, the frontend never calls it.
@app.get("/health", response_model=HealthOut, include_in_schema=False)
async def get_health() -> HealthOut:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return HealthOut(status="ok")
