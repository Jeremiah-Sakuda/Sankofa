"""
Knowledge base query interface.
Assembles grounding context from the cultural knowledge base.
"""

from app.knowledge.caribbean import REGIONS as CARIB_REGIONS
from app.knowledge.east_africa import GENERAL_EAST_AFRICA
from app.knowledge.east_africa import REGIONS as EA_REGIONS
from app.knowledge.south_asia import REGIONS as SA_REGIONS
from app.knowledge.west_africa import (
    GENERAL_WEST_AFRICA,
    get_decade_data,
)
from app.knowledge.west_africa import (
    get_region_data as wa_get_region,
)
from app.models.schemas import UserInput

CARIBBEAN_KEYWORDS = {
    "jamaica": "jamaica",
    "jamaican": "jamaica",
    "haiti": "haiti",
    "haitian": "haiti",
    "trinidad": "trinidad",
    "tobago": "trinidad",
    "caribbean": "jamaica",
}

EAST_AFRICA_KEYWORDS = {
    "kenya": "kenya",
    "kenyan": "kenya",
    "kikuyu": "kenya",
    "luo": "kenya",
    "maasai": "kenya",
    "mombasa": "kenya",
    "nairobi": "kenya",
    "tanzania": "tanzania",
    "tanzanian": "tanzania",
    "tanganyika": "tanzania",
    "zanzibar": "tanzania",
    "swahili": "tanzania",
    "nyerere": "tanzania",
    "kilimanjaro": "tanzania",
    "ethiopia": "ethiopia",
    "ethiopian": "ethiopia",
    "amhara": "ethiopia",
    "oromo": "ethiopia",
    "tigray": "ethiopia",
    "haile selassie": "ethiopia",
    "addis ababa": "ethiopia",
    "rastafari": "ethiopia",
    "abyssinia": "ethiopia",
    "east africa": "kenya",
    "east african": "kenya",
}

SOUTH_ASIA_KEYWORDS = {
    "punjab": "india_punjab",
    "punjabi": "india_punjab",
    "sikh": "india_punjab",
    "bengal": "india_bengal",
    "bengali": "india_bengal",
    "bangladesh": "india_bengal",
    "calcutta": "india_bengal",
    "kolkata": "india_bengal",
}

# Map region keys to their general context dicts (if available)
_REGION_GENERAL_CONTEXT = {}
for _key in ("ghana", "nigeria", "senegambia", "dahomey", "sierra_leone"):
    _REGION_GENERAL_CONTEXT[_key] = GENERAL_WEST_AFRICA
for _key in ("kenya", "tanzania", "ethiopia"):
    _REGION_GENERAL_CONTEXT[_key] = GENERAL_EAST_AFRICA


def _get_general_context(region_data: dict) -> dict | None:
    """Return the general context dict for a matched region, or None."""
    region_group = region_data.get("_region_group")
    if region_group == "west_africa":
        return GENERAL_WEST_AFRICA
    if region_group == "east_africa":
        return GENERAL_EAST_AFRICA
    return None


def _find_region(query: str) -> dict | None:
    """Search all knowledge bases for matching region."""
    q = query.lower()

    # Try West Africa first
    wa = wa_get_region(q)
    if wa:
        wa["_region_group"] = "west_africa"
        return wa

    # Try East Africa
    for keyword, key in EAST_AFRICA_KEYWORDS.items():
        if keyword in q:
            region = EA_REGIONS.get(key)
            if region:
                region["_region_group"] = "east_africa"
                return region

    # Try Caribbean
    for keyword, key in CARIBBEAN_KEYWORDS.items():
        if keyword in q:
            return CARIB_REGIONS.get(key)

    # Try South Asia
    for keyword, key in SOUTH_ASIA_KEYWORDS.items():
        if keyword in q:
            return SA_REGIONS.get(key)

    return None


def build_grounding_context(user_input: UserInput) -> str:
    """Build a rich grounding context block from user input + knowledge base."""
    region_data = _find_region(user_input.region_of_origin)

    if not region_data:
        return _build_generic_context(user_input)

    decade_data = get_decade_data(region_data, user_input.time_period)
    context_parts = []

    context_parts.append(f"=== REGION: {region_data['name']} ===")
    context_parts.append(f"Modern name: {region_data['modern_name']}")
    context_parts.append(f"Colonial name: {region_data['colonial_name']}")
    context_parts.append(f"Geography: {region_data['geography']}")
    context_parts.append(f"Languages: {', '.join(region_data['languages'])}")
    context_parts.append(f"Ethnic groups: {', '.join(region_data['ethnic_groups'])}")
    context_parts.append(f"Common occupations: {', '.join(region_data['occupations'])}")
    context_parts.append(f"Trade patterns: {region_data['trade_patterns']}")
    context_parts.append(f"Diaspora connections: {region_data['diaspora_connections']}")
    context_parts.append(f"Migration patterns: {region_data['migration_patterns']}")

    if decade_data:
        context_parts.append(f"\n=== ERA DETAILS ({user_input.time_period}) ===")
        context_parts.append(f"Key events: {'; '.join(decade_data.get('events', []))}")
        context_parts.append(f"Daily life: {decade_data.get('daily_life', '')}")
        context_parts.append(f"Cultural practices: {decade_data.get('cultural_practices', '')}")

    general = _get_general_context(region_data)
    if general:
        context_parts.append("\n=== BROADER CONTEXT ===")
        context_parts.append(f"Shared cultural elements: {'; '.join(general['shared_cultural_elements'])}")

    if user_input.known_fragments:
        context_parts.append("\n=== USER-PROVIDED FRAGMENTS ===")
        context_parts.append(user_input.known_fragments)

    if user_input.language_or_ethnicity:
        context_parts.append("\n=== SPECIFIED LANGUAGE/ETHNICITY ===")
        context_parts.append(user_input.language_or_ethnicity)

    if user_input.specific_interests:
        context_parts.append("\n=== AREAS OF INTEREST ===")
        context_parts.append(user_input.specific_interests)

    return "\n".join(context_parts)


def _build_generic_context(user_input: UserInput) -> str:
    """Fallback context when region isn't in our knowledge base."""
    parts = [
        f"Region: {user_input.region_of_origin}",
        f"Time period: {user_input.time_period}",
        f"\nNote: This region is not in our detailed knowledge base. "
        f"Use your knowledge of the history, culture, geography, and people of "
        f"{user_input.region_of_origin} during {user_input.time_period} to ground the narrative.",
    ]

    if user_input.known_fragments:
        parts.append(f"\nUser-provided fragments: {user_input.known_fragments}")
    if user_input.language_or_ethnicity:
        parts.append(f"Language/ethnicity: {user_input.language_or_ethnicity}")
    if user_input.specific_interests:
        parts.append(f"Areas of interest: {user_input.specific_interests}")

    return "\n".join(parts)
