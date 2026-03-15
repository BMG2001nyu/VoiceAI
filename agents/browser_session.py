"""Browser session manager — Nova Act with Playwright fallback.

Spawns isolated browser sessions per agent to execute research objectives.
Each session is single-use: start, run objective, extract results, close.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    """Result from a browser research task."""
    extracted_text: str = ""
    source_url: str = ""
    screenshot_base64: str | None = None
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


async def run_browser_task(
    objective: str,
    agent_prompt: str,
    constraints: dict[str, Any] | None = None,
) -> BrowserResult:
    """Run a browser research task using Nova Act or Playwright fallback.

    Args:
        objective: The specific research task to perform.
        agent_prompt: System prompt for the agent type (from agents/prompts/).
        constraints: Optional constraints dict with keys like 'starting_url', 'timeout_s'.

    Returns:
        BrowserResult with extracted text, source URL, and optional screenshot.
    """
    constraints = constraints or {}
    starting_url = constraints.get("starting_url", "https://www.google.com")
    timeout_s = constraints.get("timeout_s", 120)

    # Try Nova Act first, fall back to Playwright
    try:
        return await _run_nova_act(objective, agent_prompt, starting_url, timeout_s)
    except (ImportError, Exception) as exc:
        logger.info("Nova Act unavailable (%s), falling back to Playwright", exc)
        return await _run_playwright(objective, agent_prompt, starting_url, timeout_s)


async def _run_nova_act(
    objective: str,
    agent_prompt: str,
    starting_url: str,
    timeout_s: int,
) -> BrowserResult:
    """Run task using Amazon Nova Act SDK."""
    from nova_act import NovaAct  # type: ignore[import-untyped]

    async with NovaAct(
        starting_page=starting_url,
        headless=True,
    ) as agent:
        full_prompt = f"{agent_prompt}\n\nObjective: {objective}"
        result = await asyncio.wait_for(
            agent.act(full_prompt),
            timeout=timeout_s,
        )

        screenshot = None
        try:
            screenshot = await agent.screenshot()  # base64 PNG
        except Exception as exc:
            logger.warning("Screenshot capture failed: %s", exc)

        return BrowserResult(
            extracted_text=result.response if hasattr(result, 'response') else str(result),
            source_url=result.url if hasattr(result, 'url') else starting_url,
            screenshot_base64=screenshot,
            success=True,
            metadata={"engine": "nova_act"},
        )


async def _run_playwright(
    objective: str,
    agent_prompt: str,
    starting_url: str,
    timeout_s: int,
) -> BrowserResult:
    """Fallback: use Playwright for browsing + Nova Lite for reasoning."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Neither nova_act nor playwright is installed")
        return BrowserResult(
            success=False,
            error="No browser engine available (install playwright or nova_act)",
        )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Navigate to starting URL
            await page.goto(starting_url, wait_until="domcontentloaded", timeout=30000)

            # If starting from Google, search for the objective
            if "google.com" in starting_url:
                search_query = _extract_search_query(objective)
                await page.fill('textarea[name="q"], input[name="q"]', search_query)
                await page.press('textarea[name="q"], input[name="q"]', "Enter")
                await page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Click first relevant result
                try:
                    first_result = page.locator("h3").first
                    await first_result.click(timeout=5000)
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass  # Stay on search results

            # Extract page content
            content = await page.evaluate("""() => {
                const sel = document.querySelectorAll('article, main, [role="main"], .content, #content, body');
                const el = sel[0] || document.body;
                return el.innerText.slice(0, 15000);
            }""")

            current_url = page.url

            # Take screenshot
            screenshot_b64 = None
            try:
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            except Exception as exc:
                logger.warning("Screenshot failed: %s", exc)

            # Use Nova Lite for reasoning about the content if available
            analyzed_text = await _analyze_with_lite(content, objective, agent_prompt)

            return BrowserResult(
                extracted_text=analyzed_text or content[:5000],
                source_url=current_url,
                screenshot_base64=screenshot_b64,
                success=True,
                metadata={"engine": "playwright"},
            )

        except Exception as exc:
            logger.error("Playwright task failed: %s", exc)
            return BrowserResult(
                success=False,
                error=str(exc),
                source_url=page.url if page else starting_url,
                metadata={"engine": "playwright"},
            )
        finally:
            await browser.close()


async def _analyze_with_lite(
    page_content: str,
    objective: str,
    agent_prompt: str,
) -> str | None:
    """Use Nova Lite to analyze extracted page content against the objective."""
    try:
        from models.lite_client import LiteClient
        from config import settings

        if not settings.nova_api_key:
            return None

        client = LiteClient(api_key=settings.nova_api_key)
        prompt = (
            f"{agent_prompt}\n\n"
            f"OBJECTIVE: {objective}\n\n"
            f"PAGE CONTENT:\n{page_content[:10000]}\n\n"
            "Extract the most relevant findings for the objective. "
            "Return a structured summary with specific claims and supporting evidence."
        )
        response = await client.chat(prompt)
        return response
    except Exception as exc:
        logger.warning("Nova Lite analysis failed: %s", exc)
        return None


def _extract_search_query(objective: str) -> str:
    """Extract a search-engine-friendly query from the objective text."""
    # Take the first 100 chars and clean up for search
    query = objective[:100].strip()
    # Remove common instruction prefixes
    for prefix in ("Search for ", "Find ", "Look up ", "Scrape ", "Retrieve ", "Check "):
        if query.startswith(prefix):
            query = query[len(prefix):]
            break
    return query
