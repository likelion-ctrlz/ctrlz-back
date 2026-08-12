# Backend — Claude Context

## 이 레포 역할

FastAPI 메인 서버. 인증, DB, 비즈니스 로직 + AI 로직까지 이 레포 안에서 담당
AI는 별도 서버로 분리하지 않고 `ai/` 폴더에 직접 구현 (아래 "AI 연동" 섹션 참고)

## 작업 순서

1. DB 설계 (ER 다이어그램 기반 모델 정의)
2. API 엔드포인트 구현
3. `ai/` 폴더에 AI 파트가 로직 구현 → 백엔드에서 import해서 연동

## 기술 스택

- FastAPI
- SQLAlchemy + PostgreSQL (Supabase)
- 배포: Railway (무료 티어 $5 크레딧 / 2주 충분)

## 인프라 구성

```
백엔드 서버 (AI 포함) → Railway
DB                  → Supabase (PostgreSQL)
파일 저장            → AWS S3
프론트               → Vercel
```

## 소셜 로그인

- 카카오, 구글 두 가지만 구현
- 애플: 개발자 계정 필요로 제외
- 네이버: 앱 승인 시간 문제로 제외

## 디렉토리 구조

```
backend/
├── main.py           # FastAPI 앱 진입점
├── database.py       # DB 연결 (Supabase PostgreSQL)
├── routers/          # API 엔드포인트
│   ├── auth.py       # POST /auth/kakao, POST /auth/google
│   ├── missions.py   # GET /missions/recommended, POST /missions/{id}/submit
│   ├── diary.py      # POST /diary/entries, GET /diary/summary
│   └── tokens.py     # GET /tokens/balance
├── models/           # SQLAlchemy DB 모델
│   ├── user.py
│   ├── mission.py
│   └── diary.py
├── ai/               # AI 파트 구현 영역 (직접 import 방식)
│   ├── __init__.py
│   └── ai_service.py # get_mission, summarize_diary — 백엔드 ↔ AI 인터페이스
└── docs/
    └── api.md        # API 명세
```

## 환경변수 (.env)

```
# 카카오 로그인
KAKAO_CLIENT_ID=
KAKAO_REDIRECT_URI=

# 구글 로그인
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# DB (Supabase)
DATABASE_URL=

# JWT
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BUCKET_NAME=
AWS_REGION=ap-northeast-2
```

## API 응답 형식

항상 아래 형식으로 통일

```python
# 성공
{"status": "success", "data": {...}}

# 실패
{"status": "error", "message": "에러 메시지"}
```

## AI 연동 (확정 — 직접 import 방식)

AI가 백엔드 레포 안에 함께 들어가는 것으로 확정됨. 별도 서버/HTTP 호출 없이 `ai/` 폴더를 직접 import 해서 사용.
`ai/ai_service.py`의 함수 시그니처가 백엔드 ↔ AI 파트 간 인터페이스이며, 구현은 AI 파트가 담당.

```python
from ai.ai_service import get_mission, summarize_diary

mission = get_mission(level=2, user_type="은둔형")
summary = summarize_diary(entries=["오늘의 기록", ...])
```

> 새 AI 기능이 필요하면 `ai/ai_service.py`에 함수 시그니처부터 추가하고 AI 파트에 공유할 것. 라우터에서는 이 함수를 그대로 import해서 호출

## 카카오 로그인 플로우

1. 프론트가 카카오 SDK로 액세스 토큰 받음
2. `POST /auth/kakao` 로 토큰 전달
3. 백엔드가 카카오 API로 유저 정보 조회
4. users 테이블 upsert (첫 로그인 = 자동 가입)
5. JWT 발급해서 반환

## 구글 로그인 플로우

1. 프론트가 구글 SDK로 ID 토큰 받음
2. `POST /auth/google` 로 토큰 전달
3. 백엔드가 구글 API로 유저 정보 조회
4. users 테이블 upsert (첫 로그인 = 자동 가입)
5. JWT 발급해서 반환

## 배포 시 주의사항

- Railway 무료 티어는 일정 시간 미사용 시 슬립 → 발표 전 API 한 번 호출해서 깨워둘 것
- Supabase 무료 티어로 2주 운영 충분

## 브랜치 · 커밋

파트별 prefix로 구분

- 브랜치: `feat/backend/기능명` (백엔드), `feat/ai/기능명` (AI 파트) — 예: feat/backend/kakao-auth, feat/ai/mission-recommend
- 커밋: `[BE] feat: 카카오 로그인 JWT 발급 구현` (백엔드), `[AI] feat: 미션 추천 모델 연동` (AI 파트)
- 타입: feat | fix | refactor | docs | chore
- `ai/` 폴더 변경은 `[AI]` prefix, 그 외 백엔드 코드 변경은 `[BE]` prefix 사용

## 작업 시 주의사항

- .env 파일 절대 커밋 금지
- `ai/` 폴더는 AI 파트 작업 영역 — 백엔드에서는 함수 시그니처만 정의/합의하고 구현은 AI 파트에 맡길 것
- 엔드포인트 추가/변경 시 docs/api.md 업데이트 필수
