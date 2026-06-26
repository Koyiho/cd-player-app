import requests
from flask import Flask, jsonify

app = Flask(__name__)

HEADERS = {'User-Agent': 'CDPlayerApp/1.0 (study project)'}

BILLIE_ID = 'f4abc0b5-3f7a-4eff-8f78-ac078dbce533'

@app.route('/')
def home():
    return '<h1>CD Player 서버 작동 중</h1>'

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
        result.append({
            'title': album.get('title'),
            'year': album.get('first-release-date', '')[:4],
            'id': album.get('id')
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
