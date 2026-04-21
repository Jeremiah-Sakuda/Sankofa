"""Shared Firestore client singleton.

All modules that need Firestore access should import get_client() from here
to avoid creating multiple connection pools.
"""

import logging
from typing import Optional

from google.cloud import firestore

from app.config import settings

logger = logging.getLogger(__name__)

# Singleton client instance
_client: Optional[firestore.Client] = None


def get_client() -> firestore.Client:
    """Get or create the shared Firestore client.

    This ensures all modules share a single connection pool,
    reducing connection overhead and latency.
    """
    global _client
    if _client is None:
        if not settings.GOOGLE_CLOUD_PROJECT:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Firestore")
        _client = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        logger.info("Firestore client initialized for project: %s", settings.GOOGLE_CLOUD_PROJECT)
    return _client
