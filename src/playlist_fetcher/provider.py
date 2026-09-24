"""Unofficial SpotifyDown provider; its API may change without notice."""
import re
import time
from urllib.parse import urlparse
import requests

BASE = "https://api.spotifydown.com"
HEADERS = {"Accept": "application/json", "Origin": "https://spotifydown.com", "Referer": "https://spotifydown.com/", "User-Agent": "PlaylistFetcher/0.1"}


def playlist_id(value: str) -> str:
    """Accept a Spotify playlist ID, URL, or spotify:playlist: URI."""
    value = value.strip()
    if value.startswith("spotify:playlist:"):
        value = value.split(":")[-1]
    elif value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.hostname not in ("open.spotify.com", "play.spotify.com"):
            raise ValueError("Expected a Spotify playlist URL")
        match = re.fullmatch(r"/playlist/([A-Za-z0-9]+)/*", parsed.path)
        if not match:
            raise ValueError("Expected a Spotify playlist URL")
        value = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9]{10,64}", value):
        raise ValueError("Invalid playlist ID")
    return value


def get_json(session, url, *, params=None, attempts=4):
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, headers=HEADERS, timeout=(8, 30))
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code not in (429, 500, 502, 503, 504):
                raise
            if attempt == attempts - 1:
                raise
            retry_after = response.headers.get("Retry-After") if 'response' in locals() and response.status_code == 429 else None
            try:
                delay = min(30, float(retry_after)) if retry_after else min(2 ** attempt, 8)
            except ValueError:
                delay = min(2 ** attempt, 8)
            time.sleep(delay)


def tracks(session, pid):
    result, offset, seen = [], 0, set()
    while offset is not None:
        if offset in seen:
            raise RuntimeError("Provider returned a repeated pagination offset")
        seen.add(offset)
        data = get_json(session, f"{BASE}/trackList/playlist/{pid}", params={"offset": offset})
        if data.get("success") is False:
            raise RuntimeError(f"Playlist request failed: {data.get('message', 'unknown error')}")
        batch = data.get("trackList")
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected playlist response from SpotifyDown")
        result.extend(t for t in batch if isinstance(t, dict) and t.get("id"))
        next_offset = data.get("nextOffset")
        offset = int(next_offset) if next_offset is not None else None
    return result


def audio_url(session, track_id):
    if not re.fullmatch(r"[A-Za-z0-9]+", str(track_id)):
        raise ValueError("Invalid track ID")
    data = get_json(session, f"{BASE}/download/{track_id}")
    if data.get("success") is False or not data.get("link"):
        raise RuntimeError(f"No download link: {data.get('message', 'provider returned no link')}")
    url = data["link"]
    if urlparse(url).scheme != "https":
        raise RuntimeError("Provider returned a non-HTTPS download URL")
    return url
