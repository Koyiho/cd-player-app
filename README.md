# 🎵 CD Player App

> CD를 넣으면 앨범 커버, 트랙리스트, 싱크 가사를 자동으로 보여주는 웹앱.  
> 개발 경험 없이 AI와 함께 만든 첫 번째 프로젝트.

---

## 🚀 실행 방법

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. 서버 실행
python3 server.py

# 3. 브라우저에서 열기
http://127.0.0.1:5000
```

---

## 🔍 현재 가능한 것

- 아티스트 이름으로 검색
  - `/api/search/billie eilish`
- 아티스트 ID로 앨범 목록 조회
  - `/api/albums/{artist_id}`

---

## 🛠 기술 스택

| 역할 | 기술 |
|------|------|
| 백엔드 | Python + Flask |
| 음악 정보 | MusicBrainz API |
| 앨범 커버 | Cover Art Archive |
| 가사 | LRCLIB API (예정) |
| 프론트엔드 | HTML / CSS / JS (예정) |

---

## 🗺 로드맵

- [x] Flask 서버 구축
- [x] MusicBrainz API 연동
- [x] 아티스트 / 앨범 검색
- [ ] 앨범 커버 이미지 표시
- [ ] 트랙리스트 UI
- [ ] 싱크 가사 (LRCLIB)
- [ ] CD 자동 인식 (Windows)

---

## 📝 개발 과정

이 프로젝트는 개발 경험 없이 Claude AI와 함께 만들었습니다.  
막히는 부분마다 AI에게 물어보며 하나씩 해결해나가는 방식으로 진행 중입니다.

