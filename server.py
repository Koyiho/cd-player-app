import requests
import json
import os
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

HEADERS = {'User-Agent': 'CDPlayerApp/1.0 (study project)'}
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_get(key):
    path = os.path.join(CACHE_DIR, key + '.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def cache_set(key, data):
    path = os.path.join(CACHE_DIR, key + '.json')
    with open(path, 'w') as f:
        json.dump(data, f)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/search/<artist>')
def search_artist(artist):
    cached = cache_get(f'artist_{artist.lower()}')
    if cached:
        return jsonify(cached)
    url = f'https://musicbrainz.org/ws/2/artist/?query={artist}&fmt=json'
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    artists = data.get('artists', [])
    if not artists:
        return jsonify({'error': 'artist not found'})
    top = artists[0]
    result = {
        'name': top.get('name'),
        'id': top.get('id'),
        'country': top.get('country', 'unknown')
    }
    cache_set(f'artist_{artist.lower()}', result)
    return jsonify(result)

@app.route('/api/albums/<artist_id>')
def get_albums(artist_id):
    cached = cache_get(f'albums_{artist_id}')
    if cached:
        return jsonify(cached)
    url = f'https://musicbrainz.org/ws/2/release-group/?artist={artist_id}&type=album&fmt=json'
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    albums = data.get('release-groups', [])
    result = []
    for album in albums:
        album_id = album.get('id')
        cover_url = f'https://coverartarchive.org/release-group/{album_id}/front-250'
        result.append({
            'title': album.get('title'),
            'year': album.get('first-release-date', '')[:4],
            'id': album_id,
            'cover': cover_url
        })
    cache_set(f'albums_{artist_id}', result)
    return jsonify(result)

@app.route('/api/tracks/<release_group_id>')
def get_tracks(release_group_id):
    cached = cache_get(f'tracks_{release_group_id}')
    if cached:
        return jsonify(cached)
    url = f'https://musicbrainz.org/ws/2/release?release-group={release_group_id}&fmt=json'
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    releases = data.get('releases', [])
    if not releases:
        return jsonify([])
    release_id = releases[0].get('id')
    url2 = f'https://musicbrainz.org/ws/2/release/{release_id}?inc=recordings&fmt=json'
    res2 = requests.get(url2, headers=HEADERS)
    data2 = res2.json()
    tracks = []
    for medium in data2.get('media', []):
        for track in medium.get('tracks', []):
            length = track.get('length')
            duration = ''
            if length:
                mins = length // 60000
                secs = (length % 60000) // 1000
                duration = f'{mins}:{secs:02d}'
            tracks.append({
                'number': track.get('position'),
                'title': track.get('title'),
                'duration': duration
            })
    cache_set(f'tracks_{release_group_id}', tracks)
    return jsonify(tracks)

@app.route('/api/lyrics/<artist>/<title>')
def get_lyrics(artist, title):
    cached = cache_get(f'lyrics_{artist.lower()}_{title.lower()}')
    if cached:
        return jsonify(cached)
    url = f'https://lrclib.net/api/get?artist_name={artist}&track_name={title}'
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return jsonify({'error': 'lyrics not found'})
    data = res.json()
    result = {
        'plain': data.get('plainLyrics', ''),
        'synced': data.get('syncedLyrics', '')
    }
    cache_set(f'lyrics_{artist.lower()}_{title.lower()}', result)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
