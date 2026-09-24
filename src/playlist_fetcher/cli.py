"""Command-line entry point."""
import argparse
import csv
from pathlib import Path
import requests
from .provider import playlist_id, tracks
from .downloader import download_all


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export playlist metadata or download authorized audio via unofficial SpotifyDown")
    parser.add_argument("playlist", help="Spotify playlist URL, URI, or ID")
    parser.add_argument("--output", type=Path, default=Path.home() / "Music" / "PlaylistFetcher")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--metadata-only", action="store_true", help="Export track titles and IDs without downloading audio")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    try:
        pid = playlist_id(args.playlist)
        with requests.Session() as session:
            items = tracks(session, pid)
        folder = args.output.expanduser() / pid
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "tracks.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["position", "title", "track_id"])
            for i, item in enumerate(items, 1):
                writer.writerow([i, item.get("title", ""), item["id"]])
        print(f"Found {len(items)} tracks. Metadata: {folder / 'tracks.csv'}")
        if args.metadata_only:
            return 0
        if not items:
            return 0
        print("Audio downloads use an unofficial provider; download only content you have rights to.")
        summary = download_all(items, folder, workers=args.workers, overwrite=args.overwrite)
        print("Summary:", summary)
        return 1 if summary["failed"] else 0
    except (ValueError, requests.RequestException, RuntimeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())
