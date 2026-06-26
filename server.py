import requests
import json
import os
import unicodedata
import discid
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)
HEADERS = {'User-Agent': 'CDPlayerApp/1.0 (study project)'}
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

FAKE_CDS = [
    {'label': 'Billie Eilish - HIT ME HARD AND SOFT', 'artist': 'billie eilish'},
    {'label': 'Radiohead - OK Computer', 'artist': 'radiohead'},
    {'label': 'The Weeknd - After Hours', 'artist': 'the weeknd'},
    {'label': 'Kendrick Lamar - GNX', 'artist': 'kendrick lamar'},
    {'label': 'Frank Ocean - Blonde', 'artist': 'frank ocean'},
    {'label': 'Arctic Monkeys - AM', 'artist': 'arctic monkeys'},
    {'label': 'Lana Del Rey - Norman Fucking Rockwell', 'artist': 'lana del rey'},
]

SKIP_KEYWORDS = ['live', 'tour', 'acapella', 'commentary', 'rarities', 'remix',
                 'integrale', 'intégrale', 'singles', 'collection', 'best of',
                 'greatest hits', 'box set', 'instrumental', 'karaoke']

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

@app.route('/api/read-cd')
def read_cd():
    try:
        disc = discid.read()
        disc_id = disc.id
        cached = cache_get(f'disc_{disc_id}')
        if cached: return jsonify(cached)

        url = f'https://musicbrainz.org/ws/2/discid/{disc_id}?fmt=json&inc=recordings+artists+release-groups'
        res = requests.get(url, headers=HEADERS, timeout=10)

        if res.status_code == 404:
            return jsonify({'error': 'CD를 데이터베이스에서 찾을 수 없어요', 'disc_id': disc_id})

        data = res.json()
        releases = data.get('releases', [])
        if not releases:
            return jsonify({'error': 'CD 정보 없음', 'disc_id': disc_id})

        release = releases[0]
        artist = release.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown')
        title = release.get('title', 'Unknown')
        year = release.get('date', '')[:4]
        release_group_id = release.get('release-group', {}).get('id', '')
        cover = f'https://coverartarchive.org/release-group/{release_group_id}/front-250' if release_group_id else ''

        tracks = []
        for medium in release.get('media', []):
            for track in medium.get('tracks', []):
                l = track.get('length')
                dur = f'{l//60000}:{(l%60000)//1000:02d}' if l else ''
                tracks.append({
                    'number': track.get('position'),
                    'title': track.get('title'),
                    'duration': dur
                })

        result = {
            'disc_id': disc_id,
            'artist': artist,
            'title': title,
            'year': year,
            'cover': cover,
            'release_group_id': release_group_id,
            'tracks': tracks
        }
        cache_set(f'disc_{disc_id}', result)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'CD 읽기 실패: {str(e)}'})

@app.route('/api/search/<artist>')
def search_artist(artist):
    cached = cache_get(f'artist_{artist.lower()}')
    if cached: return jsonify(cached)
    try:
        res = requests.get(f'https://musicbrainz.org/ws/2/artist/?query={artist}&fmt=json', headers=HEADERS, timeout=10)
        artists = res.json().get('artists', [])
        if not artists: return jsonify({'error': 'artist not found'})
        top = artists[0]
        result = {'name': top.get('name'), 'id': top.get('id'), 'country': top.get('country', 'unknown')}
        cache_set(f'artist_{artist.lower()}', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/albums/<artist_id>')
def get_albums(artist_id):
    cached = cache_get(f'albums_{artist_id}')
    if cached: return jsonify(cached)
    try:
        res = requests.get(f'https://musicbrainz.org/ws/2/release-group/?artist={artist_id}&type=album&fmt=json', headers=HEADERS, timeout=10)
        albums = res.json().get('release-groups', [])
        result = []
        for album in albums:
            title = album.get('title', '')
            if any(k in normalize(title) for k in SKIP_KEYWORDS): continue
            album_id = album.get('id')
            year = album.get('first-release-date', '')[:4]
            result.append({'title': title, 'year': year, 'id': album_id, 'cover': f'https://coverartarchive.org/release-group/{album_id}/front-250'})
        result.sort(key=lambda x: x['year'] or '0000', reverse=True)
        cache_set(f'albums_{artist_id}', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/tracks/<release_group_id>')
def get_tracks(release_group_id):
    cached = cache_get(f'tracks_{release_group_id}')
    if cached: return jsonify(cached)
    try:
        releases = requests.get(f'https://musicbrainz.org/ws/2/release?release-group={release_group_id}&fmt=json', headers=HEADERS, timeout=10).json().get('releases', [])
        if not releases: return jsonify([])
        data2 = requests.get(f'https://musicbrainz.org/ws/2/release/{releases[0].get("id")}?inc=recordings&fmt=json', headers=HEADERS, timeout=10).json()
        tracks = []
        for medium in data2.get('media', []):
            for track in medium.get('tracks', []):
                l = track.get('length')
                dur = f'{l//60000}:{(l%60000)//1000:02d}' if l else ''
                tracks.append({'number': track.get('position'), 'title': track.get('title'), 'duration': dur})
        cache_set(f'tracks_{release_group_id}', tracks)
        return jsonify(tracks)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/lyrics/<artist>/<title>')
def get_lyrics(artist, title):
    cached = cache_get(f'lyrics_{artist.lower()}_{title.lower()}')
    if cached: return jsonify(cached)
    try:
        res = requests.get(f'https://lrclib.net/api/get?artist_name={artist}&track_name={title}', headers=HEADERS, timeout=10)
        if res.status_code != 200: return jsonify({'error': 'lyrics not found'})
        data = res.json()
        result = {'plain': data.get('plainLyrics', ''), 'synced': data.get('syncedLyrics', '')}
        cache_set(f'lyrics_{artist.lower()}_{title.lower()}', result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
