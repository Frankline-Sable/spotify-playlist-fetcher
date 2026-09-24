from playlist_fetcher.downloader import safe_name, download_one


def test_safe_name():
    assert safe_name('a/b:c?.mp3') == 'a_b_c_.mp3'


def test_existing_file_skipped(tmp_path):
    path = tmp_path / '0001 - Song - abc.mp3'
    path.write_bytes(b'existing')
    assert download_one(1, {'id': 'abc', 'title': 'Song'}, tmp_path) == ('skipped', path.name)
