"""Pydantic schemas for evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_serializer


class EvidenceIngest(BaseModel):
    mission_id: str
    agent_id: str
    claim: str
    summary: str
    source_url: str
    snippet: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    novelty: float = Field(default=1.0, ge=0.0, le=1.0)
    theme: Optional[str] = None
    screenshot_s3_key: Optional[str] = None
    screenshot_base64: Optional[str] = None  # raw base64 PNG from browser agent


class EvidenceResponse(BaseModel):
    id: str
    mission_id: str
    agent_id: str
    claim: str
    summary: str
    source_url: str
    snippet: str
    confidence: float
    novelty: float
    theme: Optional[str] = None
    screenshot_s3_key: Optional[str] = None
    screenshot_url: Optional[str] = None  # presigned URL (generated on-the-fly)
    embedding_id: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}

    @model_serializer(mode="wrap")
    def _add_created_at(self, handler):
        """Include created_at as an ISO alias for timestamp.

        The frontend EvidenceRecord TypeScript interface uses created_at,
        so we include both fields in every serialised response.
        """
        d = handler(self)
        if "timestamp" in d:
            ts = d["timestamp"]
            # ts may already be a string (if serialised by Pydantic) or datetime
            d["created_at"] = ts if isinstance(ts, str) else ts.isoformat()
        return d
