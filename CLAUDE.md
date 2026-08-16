# Backend — Claude Context

## 이 레포 역할

FastAPI 메인 서버. 세션 인증, DB, 비즈니스 로직 + AI 로직까지 이 레포 안에서 담당.  
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

없음. 닉네임 입력 한 번으로 세션이 시작됨. (소셜 로그인 완전 제거)

## 디렉토리 구조

> 실제 구현은 `core/`·`data/` 하위 폴더 없이 플랫 구조로 되어 있음 (기능은 아래 매핑과 동일).

```
back/
├── main.py                  # FastAPI 앱 진입점
├── database.py              # DB 연결 (Supabase PostgreSQL)
├── dependencies.py          # 세션 인증 미들웨어 (get_current_user, Bearer 토큰)
├── security.py              # 세션 토큰 생성/만료 유틸
├── demo.py                  # 데모 모드 판별 유틸 (DEMO_NICKNAMES 닉네임 목록)
├── routers/
│   ├── session.py           # POST /session (닉네임 → 세션 토큰, is_demo 판별)
│   ├── users.py             # GET /users/me, PATCH /users/me
│   ├── assessment.py        # POST /assessment/submit, GET /assessment/result
│   ├── missions.py          # GET /missions/recommended, GET/{id}, POST /{id}/submit 등
│   ├── diary.py             # POST /diary/entries, GET /diary/entries, GET /diary/summary
│   ├── tokens.py            # GET /tokens/balance, GET /tokens/history
│   ├── hobbies.py           # GET /hobbies/recommended, POST /{id}/apply
│   ├── programs.py          # GET /programs
│   └── reports.py           # GET /reports/daily
├── models/
│   ├── user.py              # User (character/assessment/is_demo 필드 포함)
│   ├── session.py           # Session
│   ├── mission.py           # Mission, MissionCompletion
│   ├── token.py             # TokenWallet, TokenTransaction
│   ├── hobby.py             # HobbyActivity, HobbyParticipation
│   ├── diary.py             # DiaryEntry
│   ├── program.py           # Program, ProgramReferral
│   └── report.py            # DailyReport
├── seed_missions.py         # 미션 목데이터 (PM 확정 목록, 하드코딩) + DB 시딩 스크립트
├── services/
│   ├── s3.py                # S3 파일 업로드
│   ├── assessment.py        # 자가진단 점수 계산 로직 (순수 함수)
│   ├── character.py         # 캐릭터 레벨업 로직 (순수 함수)
│   └── everlearning.py      # 취미활동 폴백용 공공데이터 API 연동
├── ai/
│   ├── __init__.py
│   └── ai_service.py        # verify_photo, transcribe_diary, summarize_diary — 백엔드↔AI 인터페이스
└── docs/
    └── api.md               # API 명세 요약
```

## 환경변수 (.env)

```
# DB (Supabase)
DATABASE_URL=

# 세션
SESSION_EXPIRE_DAYS=30

# AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BUCKET_NAME=
AWS_REGION=ap-northeast-2

# AI 서버
AI_SERVER_URL=

# 데모 모드 닉네임 목록 (쉼표 구분)
DEMO_NICKNAMES=심사위원1,심사위원2,멋사,테스트
```

## API 응답 형식

항상 아래 형식으로 통일

```python
# 성공
{"status": "success", "data": {...}}

# 실패
{"status": "error", "message": "에러 메시지"}
```

## 자가진단 로직 (확정)

8문항, 3개 축으로 구성된 자체 설계 척도. HQ-25 및 서울시 고립 척도 기반.

### 축 구성

| 축                     | 문항                                                      | 만점 |
| ---------------------- | --------------------------------------------------------- | ---- |
| 은둔축 (물리적 위축)   | Q1 외출빈도(0~4), Q2 두문불출(0~3), Q3 지속기간(0~4)      | 11점 |
| 고립축 (관계 결핍)     | Q4 오프라인 접촉(0~4), Q5 관계형태(0~3), Q6 지지체계(0~3) | 10점 |
| 심각도축 (공통 위험도) | Q7 소속여부(0~3), Q8 정서상태(0~3)                        | 6점  |

### 1단계 — 스크리닝 게이트

```
핵심위험점수 = 은둔축 원점수 + 고립축 원점수 (만점 21점)
핵심위험점수 / 21 < 0.42  →  관찰군으로 분류, 이후 처리 생략
```

### 2단계 — 유형 판정 (게이트 통과자만)

```python
hq_pct  = (Q1+Q2+Q3) / 11 * 100   # 은둔축 비율
si_pct  = (Q4+Q5+Q6) / 10 * 100   # 고립축 비율
sv_pct  = (Q7+Q8)    / 6  * 100   # 심각도축 비율

# 은둔형 조건: 은둔축 ≥42% AND Q3 ≥ 2 (6개월 이상 — 보건복지부 정의)
is_hikikomori = hq_pct >= 42 and Q3 >= 2
is_isolated   = si_pct >= 42

if is_hikikomori and is_isolated:   user_type = "복합형"
elif is_hikikomori:                  user_type = "은둔형"
elif is_isolated:                    user_type = "고립형"
else:                                user_type = "관찰군"
```

### 3단계 — 레벨 산정 (1~4)

```python
overall = (hq_pct + si_pct + sv_pct) / 3

if overall >= 75:      assessment_level = 1   # 가장 심각
elif overall >= 50:    assessment_level = 2
elif overall >= 25:    assessment_level = 3
else:                  assessment_level = 4   # 가장 안심

# 관찰군은 무조건 레벨 4
if user_type == "관찰군":
    assessment_level = 4

# 홈 표시용 점수 (10점 만점, 높을수록 심각)
assessment_display_score = round(overall / 10)  # 0~10
```

> 구현 파일: `services/assessment.py` — 순수 함수로 작성해 테스트 용이하게 유지

## 캐릭터 시스템

User 테이블에 캐릭터 관련 필드가 추가됨. 캐릭터명: **모로(Morro)**

### 레벨·XP 구조

```python
# 캐릭터 레벨: 1~4
# 전원 공통: 미션 승인 1건 = 무조건 character_level += 1 (XP 임계값 무시, 아래 "레벨업 규칙" 참고)
# XP_THRESHOLDS는 레벨업을 게이팅하지 않고 진행률 표시(next_level_xp)에만 쓰임
XP_THRESHOLDS = {1: 0, 2: 30, 3: 70, 4: 120}
```

### 캐릭터 외형 매핑

```python
CHARACTER_STAGES = {
    1: {"name": "알",        "image": "egg"},
    2: {"name": "아기 모로", "image": "baby_morro"},
    3: {"name": "꼬마 모로", "image": "kid_morro"},
    4: {"name": "모로",      "image": "morro"},
}
```

### 레벨업 규칙 (전원 공통, 확정)

**행사 현장 참여자를 포함한 전체 유저**가 대상. 데모/일반 구분 없이,
미션을 하나 승인(approved)받을 때마다 XP 임계값과 무관하게 **무조건 character_level += 1**
(MAX_LEVEL=4에서 정지). XP는 계속 누적되지만 레벨업 게이팅에는 더 이상 쓰이지 않고
진행률 표시(`next_level_xp`)용으로만 남는다.

> ⚠️ 과거 버전에서는 "데모 모드만 무조건 레벨업, 일반 모드는 XP 임계값 기반"이었으나,
> 현재는 전체 유저로 확장됨. `is_demo` 자체는 여전히 존재하지만 아래 "와우포인트 우선 노출" 용도로만 쓰인다.

### 데모 모드

- `DEMO_NICKNAMES` 환경변수에 등록된 닉네임 사용자에게 적용 (`is_demo=True`)
- 추천 미션 조회 시 "와우포인트"(`is_wow=True`) 미션을 후보 중 우선 선택해서 노출
- 레벨업 자체는 위 규칙대로 전원 동일하게 무조건 처리됨 (데모 전용 특례 아님)

> 구현 파일: `demo.py`, `services/character.py`

## 미션 시스템

### 추천 알고리즘 (레벨별 난이도 범위, 확정)

미션 `difficulty`는 **1~7 스케일**. 자가진단 레벨(assessment_level)마다 겹치는 난이도 구간을 매핑해서
그 범위 안의 미션들을 추천 목록으로 반환한다 (레벨이 올라갈수록 시작점이 2씩 밀리는 등차 구간):

| 자가진단 레벨 | 추천 난이도 범위 |
| -------------- | ---------------- |
| 1 (가장 심각)  | 1~3              |
| 2              | 3~5              |
| 3              | 4~6              |
| 4 (관찰군 포함)| 5~7              |

- 자가진단 미완료 유저: 전체 난이도(1~7) 노출
- 인접 레벨끼리 구간이 겹치므로(예: 레벨2와 레벨3 모두 4~5 포함) 같은 미션이 여러 레벨에 걸쳐 추천될 수 있음 — 의도된 설계
- `user_id` 해시로 후보를 결정론적으로 정렬해 유저마다 다른 순서로 보이게 하되, 같은 유저는 새로고침해도 동일한 결과
- 데모 모드(`is_demo=True`) 유저는 `is_wow=True` 미션을 목록 앞쪽에 우선 배치
- 오늘 이미 승인(approved)된 미션은 후보에서 제외
- `GET /missions/recommended`의 `limit` 쿼리 파라미터로 반환 개수 조절 (기본 5)
- 미션 데이터는 `seed_missions.py`에 하드코딩 후 앱 시작 시 DB 시딩 (PM 확정 미션 목록 반영)
- `target_level`은 더 이상 추천 필터링에 쓰이지 않음 (필터링은 `difficulty` 범위로 직접 함) — 어느 레벨 구간에 걸치는지 보여주는 정보성 필드로만 남음

> 구현 파일: `services/missions.py` (LEVEL_DIFFICULTY_MAP, 범위 계산 순수 함수)

### 사진 인증 흐름

```
프론트 → POST /missions/{id}/submit (multipart: photo + gps + taken_at)
  → S3 업로드
  → AI 사진 판별 (ai/ai_service.py)  # TODO: 연동 전까지 Mock(verdict=True)
  → 인증 성공 시: XP + 토큰 지급, 캐릭터 레벨업 체크
  → 응답: xp_earned, token_earned, leveled_up, character_level, next_level_xp
```

## 대화형 일기장

챗봇과 일기장을 통합한 "말하는 일기장". 날짜별로 하나의 대화 세션이 생성됨.

```
프론트 → POST /diary/message {date, content, audio_url?}
  → AI가 공감 응답 + 다음 질문 생성 (ai/ai_service.py)
  → DiaryMessage에 유저·AI 메시지 pair 저장
  → 응답: ai_reply, emotion_hint, risk_flag
```

- 하루 첫 메시지: AI가 "오늘 하루 어땠어요?" 류의 시작 질문으로 응대
- 위기 신호(`risk_flag=True`) 감지 시: 응답에 `crisis_resources` 포함 (109 등)
- 의료·진단 언급 금지: AI 프롬프트에 명시

## 지역 기관 & 취미활동

MVP 범위에서는 **하드코딩 목데이터** 사용.

- `data/programs_seed.py`: 서울 지역 고립·은둔 청년 지원 기관 10~20개
- `data/hobbies_seed.py`: 실제 존재하는 팝업·원데이클래스·공방 10~20개
- 오픈 API는 이후 연동 검토 (현재 서울 평생학습포털은 대상 부적합으로 보류)
- 취미활동 신청: 앱 내 토큰으로 결제하는 로직 (실제 외부 결제 없음)

## AI 연동 (인터페이스)

```python
# ai/ai_service.py

async def verify_mission_photo(photo_url: str, mission_title: str, conditions: list[str]) -> dict:
    """
    Returns: {"verdict": bool, "feedback": str}
    TODO: 실제 멀티모달 모델 연동 전까지 Mock(verdict=True) 사용
    """

async def get_diary_response(
    user_message: str,
    conversation_history: list[dict],  # [{"role": "user"|"ai", "content": str}]
    user_type: str,
    assessment_level: int,
) -> dict:
    """
    Returns: {"ai_reply": str, "emotion_hint": str, "risk_flag": bool}
    TODO: Claude API 연동
    """
```

> 새 AI 기능 필요 시 `ai/ai_service.py`에 함수 시그니처 먼저 추가하고 AI 파트에 공유

## 세션 인증 미들웨어

```python
# core/auth.py
async def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    session = db.query(SessionModel).filter(
        SessionModel.token == token,
        SessionModel.expires_at > datetime.utcnow()
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.")
    return session.user_id
```

## 배포 시 주의사항

- Railway 무료 티어는 일정 시간 미사용 시 슬립 → 발표 전 API 한 번 호출해서 깨워둘 것
- Supabase 무료 티어로 2주 운영 충분
- 앱 시작 시 `data/*_seed.py`로 목데이터 시딩 실행 (중복 방지 로직 포함)

## 브랜치 · 커밋

- 브랜치: `feat/backend/기능명` / `feat/ai/기능명`
- 커밋: `[BE] feat: ...` / `[AI] feat: ...`
- 타입: feat | fix | refactor | docs | chore
- `ai/` 폴더 변경 → `[AI]` prefix, 그 외 → `[BE]` prefix

## 작업 시 주의사항

- `.env` 파일 절대 커밋 금지
- `ai/` 폴더는 AI 파트 작업 영역 — 백엔드는 함수 시그니처만 정의·합의, 구현은 AI 파트
- 엔드포인트 추가/변경 시 `docs/api.md` 업데이트 필수
- 목데이터(`data/` 폴더)는 DB 시딩 스크립트로 관리, 직접 SQL 삽입 금지
