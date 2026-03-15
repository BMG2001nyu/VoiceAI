"""Agent prompt loader."""
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def load_prompt(agent_type: str) -> str:
    """Load the system prompt for the given agent type.

    Args:
        agent_type: One of OFFICIAL_SITE, NEWS_BLOG, REDDIT_HN, GITHUB, FINANCIAL, RECENT_NEWS, TASK_DECOMPOSITION.

    Returns:
        Prompt text.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = _PROMPT_DIR / f"{agent_type.lower()}.txt"
    return path.read_text(encoding="utf-8").strip()


def available_prompts() -> list[str]:
    """Return list of available prompt types."""
    return sorted(p.stem.upper() for p in _PROMPT_DIR.glob("*.txt"))
