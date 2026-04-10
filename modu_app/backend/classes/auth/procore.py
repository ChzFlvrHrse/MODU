import os
import time
import asyncio
import aiohttp
import dotenv
from dataclasses import dataclass, field
from typing import Optional, Union

dotenv.load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

PROCORE_CLIENT_ID = os.environ["PROCORE_CLIENT_ID"]
PROCORE_CLIENT_SECRET = os.environ["PROCORE_CLIENT_SECRET"]
PROCORE_BASE_URL = os.environ.get(
    "PROCORE_BASE_URL", "https://sandbox.procore.com")

TOKEN_URL = f"{PROCORE_BASE_URL}/oauth/token"
API_BASE = f"{PROCORE_BASE_URL}/rest/v1.0"


# ── Token cache (in-process, single worker) ───────────────────────────────────

@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0          # Unix timestamp
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def is_valid(self) -> bool:
        # Treat token as expired 60s early to avoid edge cases
        return bool(self.access_token) and time.time() < (self.expires_at - 60)


_cache = _TokenCache()


async def _fetch_token(session: aiohttp.ClientSession) -> str:
    """Request a new access token from Procore. Use x-www-form-urlencoded"""
    print(f"DEBUG fetching token from: {TOKEN_URL}")
    print(f"DEBUG client_id: {PROCORE_CLIENT_ID[:20]}...")
    payload = {
        "grant_type":    "client_credentials",
        "client_id":     PROCORE_CLIENT_ID,
        "client_secret": PROCORE_CLIENT_SECRET,
    }
    async with session.post(TOKEN_URL, data=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()

    _cache.access_token = data["access_token"]
    _cache.expires_at = time.time() + data.get("expires_in", 7200)
    return _cache.access_token

async def get_token(session: aiohttp.ClientSession) -> str:
    if _cache.is_valid():
        return _cache.access_token
    async with _cache._lock:
        # Double-check after acquiring lock
        if not _cache.is_valid():
            await _fetch_token(session)
    return _cache.access_token


# ── Base request helper ───────────────────────────────────────────────────────

async def procore_get(
    session: aiohttp.ClientSession,
    path: str,
    params: Optional[dict] = None,
) -> Union[dict, list[dict]]:
    """
    Authenticated GET against the Procore REST API.
    path: relative path e.g. '/drawing_areas/123/drawings'
    """
    token = await get_token(session)
    url = f"{API_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"DEBUG URL: {url}")
    print(f"DEBUG params: {params}")
    print(f"DEBUG token: {token[:30]}...")

    async with session.get(url, headers=headers, params=params or {}) as resp:
        body = await resp.text()
        print(f"DEBUG status: {resp.status}")
        print(f"DEBUG body: {body}")

        if resp.status == 401:
            # Token may have been invalidated — force refresh and retry once
            await _fetch_token(session)
            token = _cache.access_token
            headers["Authorization"] = f"Bearer {token}"
            async with session.get(url, headers=headers, params=params or {}) as retry:
                retry.raise_for_status()
                return await retry.json()
        resp.raise_for_status()
        return await resp.json()

# ── Connection test ───────────────────────────────────────────────────────────

async def test_connection() -> dict:
    """
    Quick connectivity test. Call this from a /procore/test route
    to verify credentials and API access before building anything else.
    """
    async with aiohttp.ClientSession() as session:
        try:
            token = await get_token(session)
            # Hit the 'me' endpoint — works in both sandbox and production
            print("TOKEN", token)
            me = await procore_get(session, "/me")
            return {
                "ok": True,
                "authenticated_as": me.get("login") or me.get("name", "unknown"),
                "base_url": PROCORE_BASE_URL,
                "token_preview": f"{token[:8]}...",
            }
        except aiohttp.ClientResponseError as e:
            return {"ok": False, "error": f"HTTP {e.status}: {e.message}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

print(asyncio.run(test_connection()))
