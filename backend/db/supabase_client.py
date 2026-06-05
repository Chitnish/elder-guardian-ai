"""Supabase client singleton backed by environment configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_client: Client | None = None


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} environment variable is not set. "
            "Define it in the process environment or in a .env file loaded by python-dotenv."
        )
    return value


def get_client() -> Client:
    """Return the module-level Supabase client singleton."""
    global _client
    if _client is None:
        url = _require_env("SUPABASE_URL")
        key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
        _client = create_client(url, key)
    return _client
