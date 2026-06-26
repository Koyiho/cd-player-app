import requests
import json
import os
import unicodedata
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)
HEADERS = {'User-Agent': 'CDPlayerApp/1.0 (study project)'}
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

FAKE_CDS = [
    {'label': 'Billie Eilish - HIT ME HARD AND SOFT', 'artist': 'billie eilish'},
    {'label': 'Radiohead - OK Computer', 'artist': 'radiohead'},
    {'label': 'The Weeknd - After Hours', 'artist': 'the weeknd'},
]

SKIP_KEYWORDS = ['live', 'tour', 'acapella', 'commentary', 'rarities', 'remix', 'integrale', 'intégrale', 'singles', 'collection', 'best of', 'greatest hits', 'box set']

def normalize(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()

def cache_get(key):
    path = os.path.join(CACHE_DIR, key.replace('/', '_') + '.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def cache_set(key, data):
    path = os.path.join(CACHE_DIR, key.replace('/', '_') + '.json')
    with open(path, 'w') as f:
        json.dump(data, f)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/fake-cds')
def fake_cds():
    return jsonify(FAKE_CDS)

@app.route('/api/search/<artist>')
def search_artist(artist):
    cached = cache_get(f'artist_{artist.lower()}')
    if cached: return jsonify(cached)
    url = f'https://musicbrainz.org/ws/2/artist/?query={artist}&fmt=json'
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    artists = data.get('artists', [])
    if not artists: return jsonify({'error': 'artist not found'})
    top = artists[0]
    result = {'name': top.get('name'), 'id': top.get('id'), 'country': top.get('country', 'unknown')}
    cache_set(f'artist_{artist.lower()}', result)
    return jsonify(result)

@app.route('/api/albums/<artist_id>')
def get_albums(artist_id):
    cached = cache_get(f'albums_{artist_id}')
    if cached: return jsonify(cached)
    url = f'https://musicbrainz.org/ws/2/release-group/?artist={artist_id}&type=album&fmt=json'
    res = requests.get(url, headers=HEADERS)
    albums = res.json().get('release-groups', [])
    result = []
    for album in albums:
        title = album.get('title', '')
        title_norm = normalize(title)
        if any(k in title_norm for k in SKIP_KEYWORDS): continue
        album_id = album.get('id')
        year = album.get('first-release-date', '')[:4]
        result.append({'title': title, 'year': year, 'id': album_id, 'cover': f'https://coverartarchive.org/release-group/{album_id}/front-250'})
    result.sort(key=lambda x: x['year'] or '0000', reverse=True)
    cache_set(f'albums_{artist_id}', result)
    return jsonify(result)

@app.route('/api/tracks/<release_group_id>')
def get_tracks(release_group_id):
    cached = cache_get(f'tracks_{release_group_id}')
    if cached: return jsonify(cached)
    releases = requests.get(f'https://musicbrainz.org/ws/2/release?release-group={release_group_id}&fmt=json', headers=HEADERS).json().get('releases', [])
    if not releases: return jsonify([])
    data2 = requests.get(f'https://musicbrainz.org/ws/2/release/{releases[0].get("id")}?inc=recordings&fmt=json', headers=HEADERS).json()
    tracks = []
    for medium in data2.get('media', []):
        for track in medium.get('tracks', []):
            l = track.get('length')
            dur = f'{l//60000}:{(l%60000)//1000:02d}' if l else ''
            tracks.append({'number': track.get('position'), 'title': track.get('title'), 'duration': dur})
    cache_set(f'tracks_{release_group_id}', tracks)
    return jsonify(tracks)

@app.route('/api/lyrics/<artist>/<title>')
def get_lyrics(artist, title):
    cached = cache_get(f'lyrics_{artist.lower()}_{title.lower()}')
    if cached: return jsonify(cached)
    res = requests.get(f'https://lrclib.net/api/get?artist_name={artist}&track_name={title}', headers=HEADERS)
    if res.status_code != 200: return jsonify({'error': 'lyrics not found'})
    data = res.json()
    result = {'plain': data.get('plainLyrics', ''), 'synced': data.get('syncedLyrics', '')}
    cache_set(f'lyrics_{artist.lower()}_{title.lower()}', result)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
