"""Main entry point for FastAPI backend gateway."""

from fastapi import FastAPI
from .gateway.ws_relay import router as relay_router

app = FastAPI()

# Include common routers
app.include_router(relay_router, tags=["relay"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/internal/dlq/count")
async def dlq_count():
    """Returns the size of the dead-letter queue (Task 13.5)."""
    # In a real app, this would query LLEN on Redis.
    # For now, return 0 or a mock value based on a query parameter for dev.
    return {"count": 0}
