import pytest
from playlist_fetcher.provider import playlist_id, tracks


def test_playlist_id_formats():
    pid = "37i9dQZF1DXcBWIGoYBM5M"
    assert playlist_id(pid) == pid
    assert playlist_id(f"spotify:playlist:{pid}") == pid
    assert playlist_id(f"https://open.spotify.com/playlist/{pid}?si=abc") == pid


def test_playlist_id_rejects_other_hosts():
    with pytest.raises(ValueError):
        playlist_id("https://evil.example/playlist/37i9dQZF1DXcBWIGoYBM5M")


def test_pagination(monkeypatch):
    from playlist_fetcher import provider
    pages = {0: {"trackList": [{"id": "a", "title": "A"}], "nextOffset": 1}, 1: {"trackList": [{"id": "b", "title": "B"}], "nextOffset": None}}
    monkeypatch.setattr(provider, "get_json", lambda session, url, params: pages[params["offset"]])
    assert [t["id"] for t in tracks(None, "test")] == ["a", "b"]
