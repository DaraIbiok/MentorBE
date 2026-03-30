"""
Video room service using Daily.co.

Creates a Daily.co room for a session and returns the join URL.
If DAILY_API_KEY is not configured, returns a placeholder URL so the
rest of the app still works during local development.
"""

import httpx
from fastapi import HTTPException

from app.core.config import settings


async def get_or_create_room(session_id: str, room_name: str | None = None) -> dict:
    """
    Ensure a Daily.co room exists for the given session.

    Returns
    -------
    dict with keys: name, url
    """
    if not settings.DAILY_API_KEY:
        # Dev fallback — return a mock room
        name = room_name or f"mentorme-{session_id[:8]}"
        return {"name": name, "url": f"https://meet.daily.co/{name}"}

    name = room_name or f"mentorme-{session_id[:8]}"
    headers = {
        "Authorization": f"Bearer {settings.DAILY_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        # Check if room already exists
        resp = await client.get(f"{settings.DAILY_API_URL}/rooms/{name}", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return {"name": data["name"], "url": data["url"]}

        if resp.status_code != 404:
            raise HTTPException(status_code=502, detail="Daily.co API error")

        # Create room
        resp = await client.post(
            f"{settings.DAILY_API_URL}/rooms",
            headers=headers,
            json={
                "name": name,
                "properties": {
                    "enable_chat": True,
                    "enable_screenshare": True,
                    "start_video_off": False,
                    "start_audio_off": False,
                    "exp": None,  # no expiry — session management is done by our app
                },
            },
        )

        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Could not create Daily.co room: {resp.text}")

        data = resp.json()
        return {"name": data["name"], "url": data["url"]}
