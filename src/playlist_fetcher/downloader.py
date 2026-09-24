"""Concurrent, resumable-by-skip file downloader."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import threading
import requests
from .provider import HEADERS, audio_url

_tls = threading.local()


def worker_session():
    if not hasattr(_tls, "session"):
        _tls.session = requests.Session()
    return _tls.session


def safe_name(value):
    name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", str(value)).strip(" .")
    return name[:160] or "untitled"


def download_one(index, track, folder, overwrite=False):
    session = worker_session()
    track_id = str(track["id"])
    title = safe_name(track.get("title") or track_id)
    # ID suffix prevents two identically titled tracks overwriting each other.
    destination = folder / f"{index:04d} - {title} - {track_id}.mp3"
    if destination.exists() and destination.stat().st_size > 0 and not overwrite:
        return "skipped", destination.name
    url = audio_url(session, track_id)
    part = destination.with_suffix(".mp3.part")
    try:
        with session.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, stream=True, timeout=(8, 90)) as response:
            response.raise_for_status()
            ctype = response.headers.get("Content-Type", "").lower()
            if "json" in ctype or "html" in ctype:
                raise RuntimeError(f"Expected audio, received {ctype}")
            with part.open("wb") as file:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if chunk:
                        file.write(chunk)
        if part.stat().st_size == 0:
            raise RuntimeError("Empty download")
        part.replace(destination)
        return "downloaded", destination.name
    finally:
        part.unlink(missing_ok=True)


def download_all(tracks, folder: Path, workers=4, overwrite=False):
    folder.mkdir(parents=True, exist_ok=True)
    results = {"downloaded": 0, "skipped": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, i, track, folder, overwrite): (i, track) for i, track in enumerate(tracks, 1)}
        for future in as_completed(futures):
            i, track = futures[future]
            try:
                status, name = future.result()
                results[status] += 1
                print(f"[{i}/{len(tracks)}] {status}: {name}", flush=True)
            except Exception as exc:
                results["failed"] += 1
                print(f"[{i}/{len(tracks)}] FAILED {track.get('title', 'unknown')}: {exc}", flush=True)
    return results
