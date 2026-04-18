"""
Research Service - Fetches research facts for display during narrative generation.

Extracts facts from the knowledge base (instant) and supplements with
Google Search grounding when coverage is sparse.
"""

import asyncio
import logging
import re

from app.knowledge.caribbean import REGIONS as CARIB_REGIONS
from app.knowledge.east_africa import GENERAL_EAST_AFRICA
from app.knowledge.east_africa import REGIONS as EA_REGIONS
from app.knowledge.loader import (
    CARIBBEAN_KEYWORDS,
    EAST_AFRICA_KEYWORDS,
    SOUTH_ASIA_KEYWORDS,
    _find_region,
)
from app.knowledge.south_asia import REGIONS as SA_REGIONS
from app.knowledge.west_africa import GENERAL_WEST_AFRICA, get_decade_data
from app.models.schemas import ResearchBundle, ResearchFact
from app.services.gemini_service import generate_text

logger = logging.getLogger(__name__)


def _extract_kb_facts(region: str, time_period: str) -> list[ResearchFact]:
    """Extract discrete facts from the knowledge base."""
    facts: list[ResearchFact] = []
    region_data = _find_region(region)

    if not region_data:
        return facts

    # Geography
    if region_data.get("geography"):
        facts.append(ResearchFact(
            fact=region_data["geography"],
            category="geography",
            confidence="knowledge_base",
        ))

    # Languages (split if comma-separated)
    languages = region_data.get("languages", [])
    if languages:
        lang_list = ", ".join(languages[:5])  # Limit to 5
        facts.append(ResearchFact(
            fact=f"Languages spoken include {lang_list}.",
            category="culture",
            confidence="knowledge_base",
        ))

    # Ethnic groups
    ethnic = region_data.get("ethnic_groups", [])
    if ethnic:
        ethnic_list = ", ".join(ethnic[:5])
        facts.append(ResearchFact(
            fact=f"Major ethnic groups include the {ethnic_list}.",
            category="culture",
            confidence="knowledge_base",
        ))

    # Diaspora connections
    if region_data.get("diaspora_connections"):
        facts.append(ResearchFact(
            fact=region_data["diaspora_connections"],
            category="diaspora",
            confidence="knowledge_base",
        ))

    # Trade patterns
    if region_data.get("trade_patterns"):
        facts.append(ResearchFact(
            fact=region_data["trade_patterns"],
            category="history",
            confidence="knowledge_base",
        ))

    # Era-specific data
    decade_data = get_decade_data(region_data, time_period)
    if decade_data:
        # Events
        events = decade_data.get("events", [])
        for event in events[:2]:  # Limit to 2 events
            facts.append(ResearchFact(
                fact=event,
                category="history",
                confidence="knowledge_base",
            ))

        # Daily life
        if decade_data.get("daily_life"):
            facts.append(ResearchFact(
                fact=decade_data["daily_life"],
                category="daily_life",
                confidence="knowledge_base",
            ))

        # Cultural practices
        if decade_data.get("cultural_practices"):
            facts.append(ResearchFact(
                fact=decade_data["cultural_practices"],
                category="culture",
                confidence="knowledge_base",
            ))

    # General context (shared cultural elements)
    region_group = region_data.get("_region_group")
    if region_group == "west_africa" and GENERAL_WEST_AFRICA.get("shared_cultural_elements"):
        elements = GENERAL_WEST_AFRICA["shared_cultural_elements"][:2]
        for el in elements:
            facts.append(ResearchFact(
                fact=el,
                category="culture",
                confidence="knowledge_base",
            ))
    elif region_group == "east_africa" and GENERAL_EAST_AFRICA.get("shared_cultural_elements"):
        elements = GENERAL_EAST_AFRICA["shared_cultural_elements"][:2]
        for el in elements:
            facts.append(ResearchFact(
                fact=el,
                category="culture",
                confidence="knowledge_base",
            ))

    return facts


async def _fetch_grounded_research(region: str, time_period: str) -> list[ResearchFact]:
    """Fetch supplemental facts via Google Search grounding."""
    prompt = f"""You are a research assistant for a heritage storytelling app.
Provide 4-5 interesting, specific historical or cultural facts about {region} during {time_period}.

Focus on:
- Daily life and customs
- Historical events and figures
- Cultural practices and traditions
- Geography and environment
- Diaspora connections (if any)

Format each fact as a single sentence. Be specific and educational, not generic.
Return ONLY the facts, one per line, no numbering or bullets."""

    try:
        response = await generate_text(prompt, grounded=True)
        if not response:
            return []

        facts: list[ResearchFact] = []
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()
            # Skip empty lines or very short lines
            if len(line) < 20:
                continue
            # Skip lines that look like headers or meta-text
            if line.startswith("#") or line.startswith("*") or line.endswith(":"):
                continue

            # Determine category based on keywords
            lower = line.lower()
            if any(kw in lower for kw in ("border", "coast", "river", "mountain", "climate", "land")):
                category = "geography"
            elif any(kw in lower for kw in ("war", "independence", "colonial", "king", "queen", "empire", "revolt")):
                category = "history"
            elif any(kw in lower for kw in ("migrat", "diaspora", "slave", "atlantic", "caribbean")):
                category = "diaspora"
            elif any(kw in lower for kw in ("food", "farm", "market", "work", "daily", "family", "village")):
                category = "daily_life"
            else:
                category = "culture"

            facts.append(ResearchFact(
                fact=line,
                category=category,
                confidence="grounded_search",
            ))

        return facts[:5]  # Limit to 5 facts

    except Exception as e:
        logger.warning("[research] Grounded search failed: %s", e)
        return []


async def fetch_research_bundle(region: str, time_period: str) -> ResearchBundle:
    """Fetch research facts for display during the waiting phase.

    First extracts facts from the knowledge base (instant), then supplements
    with Google Search grounding if coverage is sparse.

    Args:
        region: User's region of origin
        time_period: User's specified time period

    Returns:
        ResearchBundle with up to 8 facts
    """
    logger.info("[research] Fetching research for region=%s, time=%s", region, time_period)

    # Step 1: Extract from knowledge base (instant)
    kb_facts = _extract_kb_facts(region, time_period)
    logger.info("[research] Found %d KB facts for %s", len(kb_facts), region)

    facts = list(kb_facts)

    # Step 2: If sparse, supplement with Google Search
    if len(kb_facts) < 3:
        logger.info("[research] Sparse KB coverage, fetching grounded research...")
        search_facts = await _fetch_grounded_research(region, time_period)
        logger.info("[research] Got %d grounded facts", len(search_facts))
        facts.extend(search_facts)

    # Deduplicate and limit
    seen = set()
    unique_facts = []
    for f in facts:
        key = f.fact[:50].lower()  # Use first 50 chars as dedup key
        if key not in seen:
            seen.add(key)
            unique_facts.append(f)

    return ResearchBundle(
        region=region,
        time_period=time_period,
        facts=unique_facts[:8],  # Limit to 8 facts
    )
