"""
Live model catalog for the grading apps.

Queries the Anthropic Models API for the model IDs available to the configured
API key instead of hard-coding model strings in the UI pages.
"""

import logging
from typing import List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_anthropic_models(api_key: str) -> List[str]:
    """Model IDs available to this key, in API order (newest first). Failures are not cached."""
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    return [m.id for m in client.models.list(limit=100)]


def list_anthropic_models(api_key: Optional[str], default_model: Optional[str] = None) -> List[str]:
    """
    Return Anthropic model IDs for a selectbox.

    - Queries the API (cached for one hour per key).
    - On any failure (no key, network, auth) falls back to just `default_model`,
      so the app stays usable and the failure is logged.
    - If `default_model` is not in the API list it is still included first, so a
      config value is never silently dropped.
    """
    models: List[str] = []
    if api_key:
        try:
            models = list(_fetch_anthropic_models(api_key))
        except Exception as e:
            logger.warning("Anthropic model list query failed: %s", e)
    else:
        logger.warning("No Anthropic API key available; skipping model list query")

    if default_model and default_model not in models:
        models.insert(0, default_model)
    return models


def refresh_anthropic_models() -> None:
    """Clear the cached model list (e.g. from a 'Refresh models' button)."""
    _fetch_anthropic_models.clear()
