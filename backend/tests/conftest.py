"""
Pytest configuration and shared fixtures for Sankofa backend tests.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "development"
os.environ["GOOGLE_API_KEY"] = "test-api-key-for-testing"
os.environ["USE_FIRESTORE"] = "false"


@pytest.fixture
def user_input():
    """Create a sample UserInput for testing."""
    from app.models.schemas import UserInput

    return UserInput(
        family_name="Mensah",
        region_of_origin="Ghana",
        time_period="1940s",
        known_fragments="My grandmother mentioned Ashanti traditions",
        language_or_ethnicity="Akan",
        specific_interests="Gold trade and kente weaving",
    )


@pytest.fixture
def minimal_user_input():
    """Create a minimal UserInput with only required fields."""
    from app.models.schemas import UserInput

    return UserInput(
        family_name="Test",
        region_of_origin="Nigeria",
        time_period="1950s",
    )


@pytest.fixture
def session_store():
    """Create a fresh in-memory session store for testing."""
    from app.models.session import InMemorySessionStore

    return InMemorySessionStore(max_sessions=10)


@pytest.fixture
def mock_gemini_client():
    """Mock the Gemini client for testing without API calls."""
    with patch("app.services.gemini_service.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test narrative response"
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient

    # Disable rate limiting for tests
    from app.rate_limiter import limiter
    limiter.enabled = False

    # Mock Gemini before importing app
    with patch("app.services.gemini_service.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from app.main import app

        with TestClient(app) as client:
            yield client
