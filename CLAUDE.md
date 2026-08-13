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

## 인증 방식

- 소셜 로그인 없음. 닉네임 입력 한 번으로 `POST /session` 호출 → 유저 생성 + 세션 토큰 발급
- 이후 모든 요청에 `Authorization: Bearer {session_token}` 헤더 필요
- 세션 토큰은 JWT가 아니라 `sessions` 테이블에 저장되는 랜덤 문자열 (DB 조회 방식)

## 디렉토리 구조

```
backend/
├── main.py           # FastAPI 앱 진입점
├── database.py       # DB 연결 (Supabase PostgreSQL)
├── security.py       # 세션 토큰 생성
├── dependencies.py   # 세션 인증 의존성 (get_current_user)
├── routers/          # API 엔드포인트
│   ├── session.py     # POST /session (닉네임 온보딩)
│   ├── users.py        # GET/PATCH /users/me
│   ├── assessment.py   # POST /assessment/submit, GET /assessment/result
│   ├── missions.py     # GET /missions/recommended, POST /missions/{id}/submit, GET /missions/{id}/result, GET /missions/history
│   ├── tokens.py        # GET /tokens/balance, GET /tokens/history
│   ├── hobbies.py       # GET /hobbies/recommended, POST /hobbies/{id}/apply
│   ├── diary.py          # POST /diary/entries, GET /diary/entries, GET /diary/summary
│   ├── programs.py       # GET /programs, POST /programs/{id}/apply
│   └── reports.py        # GET /reports/daily
├── models/           # SQLAlchemy DB 모델
│   ├── user.py, session.py, mission.py, token.py, hobby.py, diary.py, program.py, report.py
├── services/
│   └── s3.py         # S3 업로드 (미션 인증 사진, 음성 일기)
├── ai/               # AI 파트 구현 영역 (직접 import 방식)
│   ├── __init__.py
│   └── ai_service.py # get_mission, summarize_diary — 백엔드 ↔ AI 인터페이스
└── docs/
    └── api.md        # API 명세
```

## 환경변수 (.env)

```
# DB (Supabase)
DATABASE_URL=

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

## 세션 인증 플로우

1. 프론트가 닉네임만 받아서 `POST /session` 호출
2. 백엔드가 `users` 레코드 생성 + `token_wallets` 생성 + `sessions` 레코드 생성(랜덤 토큰, 만료 30일)
3. 응답으로 `session_token` 반환 → 프론트가 보관
4. 이후 모든 요청에 `Authorization: Bearer {session_token}` 헤더 포함
5. 백엔드는 `sessions` 테이블에서 토큰 조회로 유저 식별 (`dependencies.get_current_user`)

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
