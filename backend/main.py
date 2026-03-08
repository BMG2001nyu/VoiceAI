"""Placeholder for FastAPI app. Replace with full gateway and routers."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}
