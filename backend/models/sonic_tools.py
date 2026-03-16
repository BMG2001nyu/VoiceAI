"""Sonic tool schema definitions (Task 3.2).

Defines the five tools that Nova 2 Sonic can invoke during a mission conversation.
Two formats are provided:
  - SONIC_TOOLS           Nova Realtime / OpenAI-compatible format (used by SonicClient)
  - SONIC_TOOLS_BEDROCK   Bedrock Converse toolSpec format (kept for reference/fallback)

Tool execution is handled in the Voice Gateway (Task 3.3), not here.
This module is purely schema definitions.

Tools:
    start_mission               Create and start a new intelligence mission
    get_mission_status          Check status of a running mission
    get_new_findings            Retrieve recent evidence for narration
    ask_user_for_clarification  Ask user a clarifying question
    deliver_final_briefing      Speak the completed intelligence briefing
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Nova Realtime / OpenAI-compatible format
# (injected into session.update → session.tools)
# ---------------------------------------------------------------------------

SONIC_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "start_mission",
        "description": (
            "Create and start a new intelligence-gathering mission based on the user's "
            "spoken objective. Call this as soon as you clearly understand what the user "
            "wants to research — do not ask for clarification unless the request is truly "
            "ambiguous. This deploys a fleet of browser agents immediately."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "description": (
                        "The full mission objective as spoken by the user, "
                        "e.g. 'Find Sequoia Capital's recent AI investments and partner priorities.'"
                    ),
                },
            },
            "required": ["objective"],
        },
    },
    {
        "type": "function",
        "name": "get_mission_status",
        "description": (
            "Check the current status of a running mission: how many agents are active, "
            "how many evidence items have been found, and the overall mission state. "
            "Call this proactively every few seconds while agents are working so you can "
            "keep the user informed with brief spoken updates."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mission_id": {
                    "type": "string",
                    "description": "The UUID of the mission to check.",
                },
            },
            "required": ["mission_id"],
        },
    },
    {
        "type": "function",
        "name": "get_new_findings",
        "description": (
            "Retrieve the most recent evidence findings collected by the browser agents. "
            "Call this proactively while agents are working to get new discoveries. "
            "After receiving findings, give the user a brief natural-language summary — "
            "do NOT read back raw data, URLs, or scores. Synthesize into spoken insights."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mission_id": {
                    "type": "string",
                    "description": "The UUID of the mission.",
                },
                "since_timestamp": {
                    "type": "string",
                    "description": (
                        "ISO 8601 timestamp. Only return findings after this time. "
                        "Omit to retrieve all findings."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of findings to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["mission_id"],
        },
    },
    {
        "type": "function",
        "name": "ask_user_for_clarification",
        "description": (
            "Ask the user a clarifying question when their mission objective is genuinely "
            "ambiguous and you cannot proceed without more information. Use sparingly — "
            "prefer to make a reasonable assumption and start the mission. Never ask more "
            "than one question at a time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The clarifying question to ask the user, in plain spoken language.",
                },
            },
            "required": ["question"],
        },
    },
    {
        "type": "function",
        "name": "deliver_final_briefing",
        "description": (
            "Deliver the completed intelligence briefing to the user as a spoken summary. "
            "Call this when the mission is complete and the briefing text has been "
            "synthesised. The briefing will be spoken aloud and displayed in the War Room."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mission_id": {
                    "type": "string",
                    "description": "The UUID of the completed mission.",
                },
                "briefing_text": {
                    "type": "string",
                    "description": (
                        "The full intelligence briefing text to deliver. Should be 2–3 "
                        "paragraphs, written for spoken delivery (no bullet points, "
                        "no markdown). Lead with the most important finding."
                    ),
                },
            },
            "required": ["mission_id", "briefing_text"],
        },
    },
]


# ---------------------------------------------------------------------------
# Bedrock Converse toolSpec format (Task 3.2 original spec / fallback)
# Kept for compatibility if team uses boto3 Bedrock ConversStream directly.
# ---------------------------------------------------------------------------

SONIC_TOOLS_BEDROCK: list[dict[str, Any]] = [
    {
        "toolSpec": {
            "name": "start_mission",
            "description": (
                "Create and start a new intelligence mission based on the user's spoken "
                "objective. Call this as soon as you understand the user's request."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "objective": {
                            "type": "string",
                            "description": "Full mission objective from user",
                        }
                    },
                    "required": ["objective"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_mission_status",
            "description": (
                "Check mission status proactively to keep the user updated with brief spoken reports."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "mission_id": {"type": "string"},
                    },
                    "required": ["mission_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_new_findings",
            "description": "Retrieve recent evidence findings proactively and summarize them naturally to the user.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "mission_id": {"type": "string"},
                        "since_timestamp": {
                            "type": "string",
                            "description": "ISO timestamp; return findings after this time",
                        },
                    },
                    "required": ["mission_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "ask_user_for_clarification",
            "description": (
                "Ask the user a clarifying question. Use only when the mission objective "
                "is truly ambiguous."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                    },
                    "required": ["question"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "deliver_final_briefing",
            "description": (
                "Deliver the completed intelligence briefing to the user as a spoken summary."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "mission_id": {"type": "string"},
                        "briefing_text": {"type": "string"},
                    },
                    "required": ["mission_id", "briefing_text"],
                }
            },
        }
    },
]


# ---------------------------------------------------------------------------
# Tool name lookup helpers
# ---------------------------------------------------------------------------

TOOL_NAMES: set[str] = {t["name"] for t in SONIC_TOOLS}

TOOL_MAP: dict[str, dict] = {t["name"]: t for t in SONIC_TOOLS}


def get_tool_schema(name: str) -> dict[str, Any] | None:
    """Return the Nova Realtime tool schema for a given tool name, or None."""
    return TOOL_MAP.get(name)


def validate_tool_call(name: str, arguments: dict[str, Any]) -> list[str]:
    """Validate tool call arguments against the schema.

    Returns a list of error strings (empty if valid).
    """
    schema = get_tool_schema(name)
    if schema is None:
        return [f"Unknown tool: {name!r}"]

    errors: list[str] = []
    required = schema["parameters"].get("required", [])
    for field in required:
        if field not in arguments:
            errors.append(f"Missing required argument: {field!r}")
    return errors
