
import requests, json, os, unicodedata, discid, threading, time, subprocess
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)
HEADERS = {"User-Agent": "CDPlayerApp/1.0 (study project)"}
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

FAKE_CDS = [
    {"label": "Billie Eilish - HIT ME HARD AND SOFT", "artist": "billie eilish"},
    {"label": "Radiohead - OK Computer", "artist": "radiohead"},
    {"label": "The Weeknd - After Hours", "artist": "the weeknd"},
    {"label": "Kendrick Lamar - GNX", "artist": "kendrick lamar"},
    {"label": "Frank Ocean - Blonde", "artist": "frank ocean"},
    {"label": "Arctic Monkeys - AM", "artist": "arctic monkeys"},
    {"label": "Lana Del Rey - Norman Fucking Rockwell", "artist": "lana del rey"},
]

SKIP_KEYWORDS = ["live", "tour", "acapella", "commentary", "rarities", "remix",
                 "integrale", "intgrale", "singles", "collection", "best of",
                 "greatest hits", "box set", "instrumental", "karaoke"]

cd_state = {"disc_id": None, "status": "empty"}
player_state = {"playing": False, "track": 0, "total": 0}

def normalize(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def cache_get(key):
    path = os.path.join(CACHE_DIR, key.replace("/", "_") + ".json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def cache_set(key, data):
    path = os.path.join(CACHE_DIR, key.replace("/", "_") + ".json")
    with open(path, "w") as f:
        json.dump(data, f)

def vlc_cmd(script):
    subprocess.Popen(["osascript", "-e", script])

def monitor_cd():
    last_id = None
    while True:
        try:
            disc = discid.read()
            if disc.id != last_id:
                last_id = disc.id
                cd_state["disc_id"] = disc.id
                cd_state["status"] = "inserted"
        except:
            if last_id is not None:
                last_id = None
                cd_state["disc_id"] = None
                cd_state["status"] = "empty"
        time.sleep(3)

threading.Thread(target=monitor_cd, daemon=True).start()

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/api/fake-cds")
def fake_cds():
    return jsonify(FAKE_CDS)

@app.route("/api/cd-status")
def cd_status():
    return jsonify(cd_state)

@app.route("/api/player/status")
def player_status():
    return jsonify(player_state)

@app.route("/api/player/play/<int:track>")
def play_track(track):
    try:
        script = f"""tell application "VLC"
            activate
            play item {track} of playlist 1
        end tell"""
        subprocess.Popen(["osascript", "-e", script])
        player_state["playing"] = True
        player_state["track"] = track
        return jsonify({"ok": True, "track": track})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/player/pause")
def pause():
    vlc_cmd("tell application \"VLC\" to pause")
    player_state["playing"] = not player_state["playing"]
    return jsonify({"playing": player_state["playing"]})

@app.route("/api/player/stop")
def stop():
    vlc_cmd("tell application \"VLC\" to stop")
    player_state["playing"] = False
    player_state["track"] = 0
    return jsonify({"ok": True})

@app.route("/api/player/next")
def next_track():
    vlc_cmd("tell application \"VLC\" to next")
    player_state["track"] += 1
    return jsonify({"ok": True, "track": player_state["track"]})

@app.route("/api/player/prev")
def prev_track():
    vlc_cmd("tell application \"VLC\" to previous")
    player_state["track"] -= 1
    return jsonify({"ok": True, "track": player_state["track"]})

@app.route("/api/read-cd")
def read_cd():
    try:
        disc = discid.read()
        disc_id = disc.id
        cached = cache_get("disc_" + disc_id)
        if cached:
            player_state["total"] = len(cached.get("tracks", []))
            return jsonify(cached)
        url = "https://musicbrainz.org/ws/2/discid/" + disc_id + "?fmt=json&inc=recordings+artists+release-groups"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 404:
            return jsonify({"error": "CD를 찾을 수 없어요", "disc_id": disc_id})
        releases = res.json().get("releases", [])
        if not releases:
            return jsonify({"error": "CD 정보 없음"})
        release = releases[0]
        artist = release.get("artist-credit", [{}])[0].get("artist", {}).get("name", "Unknown")
        title = release.get("title", "Unknown")
        year = release.get("date", "")[:4]
        rg_id = release.get("release-group", {}).get("id", "")
        cover = "https://coverartarchive.org/release-group/" + rg_id + "/front-250" if rg_id else ""
        tracks = []
        for medium in release.get("media", []):
            for track in medium.get("tracks", []):
                l = track.get("length")
                dur = str(l//60000) + ":" + str((l%60000)//1000).zfill(2) if l else ""
                tracks.append({"number": track.get("position"), "title": track.get("title"), "duration": dur})
        result = {"disc_id": disc_id, "artist": artist, "title": title, "year": year, "cover": cover, "tracks": tracks}
        cache_set("disc_" + disc_id, result)
        player_state["total"] = len(tracks)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/search/<artist>")
def search_artist(artist):
    cached = cache_get("artist_" + artist.lower())
    if cached: return jsonify(cached)
    try:
        res = requests.get("https://musicbrainz.org/ws/2/artist/?query=" + artist + "&fmt=json", headers=HEADERS, timeout=10)
        artists = res.json().get("artists", [])
        if not artists: return jsonify({"error": "not found"})
        top = artists[0]
        result = {"name": top.get("name"), "id": top.get("id"), "country": top.get("country", "unknown")}
        cache_set("artist_" + artist.lower(), result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/albums/<artist_id>")
def get_albums(artist_id):
    cached = cache_get("albums_" + artist_id)
    if cached: return jsonify(cached)
    try:
        res = requests.get("https://musicbrainz.org/ws/2/release-group/?artist=" + artist_id + "&type=album&fmt=json", headers=HEADERS, timeout=10)
        albums = res.json().get("release-groups", [])
        result = []
        for album in albums:
            t = album.get("title", "")
            if any(k in normalize(t) for k in SKIP_KEYWORDS): continue
            aid = album.get("id")
            year = album.get("first-release-date", "")[:4]
            result.append({"title": t, "year": year, "id": aid, "cover": "https://coverartarchive.org/release-group/" + aid + "/front-250"})
        result.sort(key=lambda x: x["year"] or "0000", reverse=True)
        cache_set("albums_" + artist_id, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/tracks/<release_group_id>")
def get_tracks(release_group_id):
    cached = cache_get("tracks_" + release_group_id)
    if cached: return jsonify(cached)
    try:
        releases = requests.get("https://musicbrainz.org/ws/2/release?release-group=" + release_group_id + "&fmt=json", headers=HEADERS, timeout=10).json().get("releases", [])
        if not releases: return jsonify([])
        data2 = requests.get("https://musicbrainz.org/ws/2/release/" + releases[0].get("id") + "?inc=recordings&fmt=json", headers=HEADERS, timeout=10).json()
        tracks = []
        for medium in data2.get("media", []):
            for track in medium.get("tracks", []):
                l = track.get("length")
                dur = str(l//60000) + ":" + str((l%60000)//1000).zfill(2) if l else ""
                tracks.append({"number": track.get("position"), "title": track.get("title"), "duration": dur})
        cache_set("tracks_" + release_group_id, tracks)
        return jsonify(tracks)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/lyrics/<artist>/<title>")
def get_lyrics(artist, title):
    cached = cache_get("lyrics_" + artist.lower() + "_" + title.lower())
    if cached: return jsonify(cached)
    try:
        res = requests.get("https://lrclib.net/api/get?artist_name=" + artist + "&track_name=" + title, headers=HEADERS, timeout=10)
        if res.status_code != 200: return jsonify({"error": "not found"})
        data = res.json()
        result = {"plain": data.get("plainLyrics", ""), "synced": data.get("syncedLyrics", "")}
        cache_set("lyrics_" + artist.lower() + "_" + title.lower(), result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
