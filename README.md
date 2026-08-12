# Backend

FastAPI 기반 메인 서버. 인증, DB, 비즈니스 로직 + AI 로직까지 이 레포에서 함께 담당합니다. (`ai/` 폴더, 직접 import 방식 — 자세한 내용은 [CLAUDE.md](./CLAUDE.md) 참고)

## 기술 스택

- FastAPI
- SQLAlchemy + PostgreSQL (Supabase)
- JWT (카카오 / 구글 소셜 로그인)
- 배포: Railway

## 시작하기

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env  # 값 채워넣기

uvicorn main:app --reload
```

Windows에서는 venv 생성·설치 후 `start.bat`을 실행하면 venv 활성화 + 서버 실행이 한 번에 됩니다.

서버 실행 후 http://localhost:8000/docs 에서 API 문서를 확인할 수 있습니다.

## 디렉토리 구조

```
.
├── main.py           # FastAPI 앱 진입점
├── database.py        # DB 연결 (Supabase PostgreSQL)
├── security.py        # JWT 발급/검증
├── dependencies.py    # 인증 의존성 (get_current_user)
├── start.bat           # Windows용 venv 활성화 + 서버 실행 스크립트
├── routers/           # API 엔드포인트
│   ├── auth.py         # POST /auth/kakao, POST /auth/google
│   ├── missions.py      # GET /missions/recommended, POST /missions/{id}/submit
│   ├── diary.py         # POST /diary/entries, GET /diary/summary
│   └── tokens.py        # GET /tokens/balance
├── models/             # SQLAlchemy DB 모델
│   ├── user.py
│   ├── mission.py
│   └── diary.py
├── ai/                 # AI 파트 구현 영역 (직접 import 방식)
│   ├── __init__.py
│   └── ai_service.py    # get_mission, summarize_diary — 백엔드 ↔ AI 인터페이스
└── docs/
    └── api.md          # API 명세
```

## 환경변수

`.env.example` 참고. `.env` 파일은 절대 커밋하지 않습니다.

## 브랜치 · 커밋 규칙

AI 파트와 백엔드 파트는 파트별 prefix로 구분합니다.

- 브랜치: `feat/backend/기능명` (백엔드) / `feat/ai/기능명` (AI 파트) — 예: `feat/backend/kakao-auth`, `feat/ai/mission-recommend`
- 커밋: `[BE] feat: 카카오 로그인 JWT 발급 구현` / `[AI] feat: 미션 추천 모델 연동`
- 타입: `feat` | `fix` | `refactor` | `docs` | `chore`

자세한 컨텍스트는 [CLAUDE.md](./CLAUDE.md)를 참고하세요.
