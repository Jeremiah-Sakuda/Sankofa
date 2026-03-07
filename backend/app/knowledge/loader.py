"""
Knowledge base query interface.
Assembles grounding context from the cultural knowledge base.
"""

from app.knowledge.west_africa import (
    REGIONS,
    GENERAL_WEST_AFRICA,
    get_region_data,
    get_decade_data,
)
from app.models.schemas import UserInput


def build_grounding_context(user_input: UserInput) -> str:
    """Build a rich grounding context block from user input + knowledge base."""
    region_data = get_region_data(user_input.region_of_origin)

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

    context_parts.append(f"\n=== BROADER WEST AFRICAN CONTEXT ===")
    context_parts.append(f"Colonial context: {GENERAL_WEST_AFRICA['colonial_context']}")
    context_parts.append(f"Shared cultural elements: {'; '.join(GENERAL_WEST_AFRICA['shared_cultural_elements'])}")
    context_parts.append(f"Transatlantic slavery: {GENERAL_WEST_AFRICA['transatlantic_slavery']}")

    if user_input.known_fragments:
        context_parts.append(f"\n=== USER-PROVIDED FRAGMENTS ===")
        context_parts.append(user_input.known_fragments)

    if user_input.language_or_ethnicity:
        context_parts.append(f"\n=== SPECIFIED LANGUAGE/ETHNICITY ===")
        context_parts.append(user_input.language_or_ethnicity)

    if user_input.specific_interests:
        context_parts.append(f"\n=== AREAS OF INTEREST ===")
        context_parts.append(user_input.specific_interests)

    return "\n".join(context_parts)


def _build_generic_context(user_input: UserInput) -> str:
    """Fallback context when region isn't in our knowledge base."""
    parts = [
        f"Region: {user_input.region_of_origin}",
        f"Time period: {user_input.time_period}",
        f"\n=== BROADER WEST AFRICAN CONTEXT ===",
        f"Colonial context: {GENERAL_WEST_AFRICA['colonial_context']}",
        f"Shared cultural elements: {'; '.join(GENERAL_WEST_AFRICA['shared_cultural_elements'])}",
    ]

    if user_input.known_fragments:
        parts.append(f"\nUser-provided fragments: {user_input.known_fragments}")
    if user_input.language_or_ethnicity:
        parts.append(f"Language/ethnicity: {user_input.language_or_ethnicity}")
    if user_input.specific_interests:
        parts.append(f"Areas of interest: {user_input.specific_interests}")

    return "\n".join(parts)
