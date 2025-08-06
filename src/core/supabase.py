from src.core.config import settings
from supabase import AsyncClientOptions
from supabase._async.client import AsyncClient, create_client


async def get_supabase_client() -> AsyncClient:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ValueError("Supabase URL and anon key must be configured")

    return await create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=AsyncClientOptions(
            postgrest_client_timeout=10, storage_client_timeout=10
        ),
    )
