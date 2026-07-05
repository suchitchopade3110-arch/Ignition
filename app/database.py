"""
Supabase client initialization ONLY.

Ledger writes, baseline reads, ACS history, and vector queries live in
app/repositories/ and app/rag/ — not here. This file's entire job is
producing a configured client for those modules to consume.
"""
from functools import lru_cache
from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)