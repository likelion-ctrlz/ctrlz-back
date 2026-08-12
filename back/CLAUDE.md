# Backend — Claude Context

## 이 레포 역할
FastAPI 메인 서버. 인증, DB, 비즈니스 로직 담당
AI 호출 방식은 추후 확정 예정 (아래 "AI 연동" 섹션 참고)

## 작업 순서
1. DB 설계 (ER 다이어그램 기반 모델 정의)
2. API 엔드포인트 구현
3. AI 호출 방식 확정 후 연동

## 기술 스택
- FastAPI
- SQLAlchemy + PostgreSQL (Supabase)
- 배포: Railway (무료 티어 $5 크레딧 / 2주 충분)

## 인프라 구성
```
백엔드 서버  → Railway
DB          → Supabase (PostgreSQL)
파일 저장    → AWS S3
프론트      → Vercel
AI 서버     → Railway (별도 서비스)
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

# AI 서버 (방식 확정 후 변경될 수 있음)
AI_SERVER_URL=http://localhost:9000
```

## API 응답 형식
항상 아래 형식으로 통일
```python
# 성공
{"status": "success", "data": {...}}

# 실패
{"status": "error", "message": "에러 메시지"}
```

## AI 연동 (방식 미확정)
AI 호출 방식은 아직 확정되지 않았음. 아래 두 가지 중 팀 논의 후 결정 예정.

**옵션 A — 직접 import (AI 코드가 백엔드 레포 안에 있을 때)**
```python
# TODO: 모듈명 확정 후 수정
from ai.ai_service import get_mission  # 임시 모듈명

result = get_mission(level=2, user_type="은둔형")
```

**옵션 B — HTTP 호출 (AI가 별도 서버로 분리될 때)**
```python
# TODO: AI_SERVER_URL 확정 후 수정
import httpx

async def call_ai_mission(level: int, user_type: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{AI_SERVER_URL}/mission",
                                json={"level": level, "user_type": user_type})
    return res.json()
```

> AI 기능이 필요한 엔드포인트는 일단 `# TODO: AI 연동 필요` 주석 남기고 Mock 값으로 구현해둘 것

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
- 브랜치: `feat/backend/기능명` (예: feat/backend/kakao-auth)
- 커밋: `[BE] feat: 카카오 로그인 JWT 발급 구현`
- 타입: feat | fix | refactor | docs | chore

## 작업 시 주의사항
- .env 파일 절대 커밋 금지
- AI 연동 방식 확정 전까지 AI 호출 부분은 Mock 값 + `# TODO: AI 연동 필요` 주석으로 처리
- AI 연동 방식 확정되면 CLAUDE.md AI 연동 섹션 업데이트 필요
- 엔드포인트 추가/변경 시 docs/api.md 업데이트 필수