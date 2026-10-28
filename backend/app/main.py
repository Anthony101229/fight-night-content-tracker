"""FastAPI application entry point. Real endpoints arrive in Phase 3."""

from fastapi import FastAPI

app = FastAPI(title="Fight Night Content Tracker")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check used to confirm the API container is up."""
    return {"status": "ok"}
