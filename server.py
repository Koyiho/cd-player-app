import requests
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

HEADERS = {'User-Agent': 'CDPlayerApp/1.0 (study project)'}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/search/<artist>')
def search_artist(artist):
    url = f'https://musicbrainz.org/ws/2/artist/?query={artist}&fmt=json'
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    artists = data.get('artists', [])
    if not artists:
        return jsonify({'error': 'artist not found'})
    top = artists[0]
    return jsonify({
        'name': top.get('name'),
        'id': top.get('id'),
        'country': top.get('country', 'unknown')
    })

@app.route('/api/albums/<artist_id>')
def get_albums(artist_id):
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
    return jsonify(result)

@app.route('/api/tracks/<release_group_id>')
def get_tracks(release_group_id):
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
    return jsonify(tracks)

@app.route('/api/lyrics/<artist>/<title>')
def get_lyrics(artist, title):
    url = f'https://lrclib.net/api/get?artist_name={artist}&track_name={title}'
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return jsonify({'error': 'lyrics not found'})
    data = res.json()
    return jsonify({
        'plain': data.get('plainLyrics', ''),
        'synced': data.get('syncedLyrics', '')
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
