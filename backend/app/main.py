"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers import crew, events, footage

app = FastAPI(
    title="Fight Night Content Tracker",
    description="Plan and track video coverage of MMA events.",
)
app.include_router(events.router)
app.include_router(crew.router)
app.include_router(footage.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check used to confirm the API container is up."""
    return {"status": "ok"}
