# API 명세

프론트 ↔ 백엔드 간 HTTP API 명세입니다. 백엔드 ↔ AI 파트 간 인터페이스는 맨 아래 [AI 인터페이스](#ai-인터페이스-aiaiservicepy) 섹션 참고 (HTTP 아님, 함수 직접 import).

모든 응답은 아래 형식을 따릅니다.

```json
// 성공
{"status": "success", "data": {}}

// 실패
{"status": "error", "message": "에러 메시지"}
```

소셜 로그인 없음. `POST /session`으로 닉네임만 입력하면 세션 토큰이 발급되고, 인증이 필요한 나머지 엔드포인트는 `Authorization: Bearer {session_token}` 헤더가 필요합니다.

## 세션

### POST /session
닉네임을 받아 유저 생성 + 세션 토큰 발급 (온보딩)

**Request**
```json
{"nickname": "숲속고양이"}
```

**Response**
```json
{
  "status": "success",
  "data": {"session_token": "abc123...", "user_id": "...", "nickname": "숲속고양이"}
}
```

## 사용자 (인증 필요)

### GET /users/me
현재 유저 정보 조회

**Response**
```json
{
  "status": "success",
  "data": {
    "user_id": "...", "nickname": "숲속고양이", "region": "서울 마포구",
    "status_level": 2, "user_type": "은둔형", "token_balance": 150
  }
}
```

### PATCH /users/me
프로필(지역) 수정

**Request**
```json
{"region": "서울 마포구"}
```

**Response**
```json
{"status": "success", "data": {"region": "서울 마포구"}}
```

## 자가진단 (인증 필요)

### POST /assessment/submit
설문 응답 제출 → 상태 레벨/유형 산출

**Request**
```json
{"answers": [3, 2, 4, 1, 3, 2, 4]}
```

**Response**
```json
{
  "status": "success",
  "data": {"status_level": 2, "user_type": "은둔형", "description": "..."}
}
```

### GET /assessment/result
가장 최근 자가진단 결과 조회

**Response**
```json
{"status": "success", "data": {"status_level": 2, "user_type": "은둔형", "assessed_at": "..."}}
```

## 미션 (인증 필요)

### GET /missions/recommended
유저 상태에 맞는 미션 목록 조회

> `ai.ai_service.get_mission` 연동 전까지는 `status_level`/`user_type` 기준 DB 조회로 대체 (`# TODO: AI 연동 필요`)

**Response**
```json
{
  "status": "success",
  "data": [
    {
      "mission_id": "...", "title": "창문 열고 3분 바람 쐬기", "description": "...",
      "difficulty": 1, "category": "외출", "verification_type": "photo", "token_reward": 10
    }
  ]
}
```

### POST /missions/{id}/submit
미션 인증 사진 업로드 → AI 판별 → 토큰 지급

> `ai.ai_service.verify_photo` 연동 전까지는 항상 승인 처리 (`# TODO: AI 연동 필요`)

**Request**: `multipart/form-data`
- `photo`: 이미지 파일
- `gps_lat`, `gps_lng`: float
- `taken_at`: ISO datetime

**Response**
```json
{
  "status": "success",
  "data": {
    "completion_id": "...", "ai_verdict": true, "ai_feedback": "잘 하셨어요!",
    "token_earned": 10, "token_balance": 160
  }
}
```

### GET /missions/{id}/result
미션 인증 결과 조회

**Response**
```json
{"status": "success", "data": {"completion_id": "...", "status": "approved", "ai_verdict": true, "ai_feedback": "...", "token_earned": 10}}
```

### GET /missions/history
미션 완료 이력 조회 (`?date=YYYY-MM-DD` 선택)

**Response**
```json
{"status": "success", "data": [{"completion_id": "...", "mission_title": "...", "status": "approved", "token_earned": 10, "completed_at": "..."}]}
```

## 토큰 (인증 필요)

### GET /tokens/balance
보유 토큰 잔액 조회

**Response**
```json
{"status": "success", "data": {"token_balance": 160}}
```

### GET /tokens/history
토큰 적립/사용 내역 조회

**Response**
```json
{"status": "success", "data": [{"tx_id": "...", "amount": 10, "reason": "mission_complete", "created_at": "..."}]}
```

## 취미활동 (인증 필요)

### GET /hobbies/recommended
유저 상태에 맞는 취미활동 목록 조회

**Response**
```json
{"status": "success", "data": [{"hobby_id": "...", "title": "실내 원예 모임", "description": "...", "category": "원예", "token_cost": 30}]}
```

### POST /hobbies/{id}/apply
토큰을 사용해 취미활동 참여 신청

**Response**
```json
{"status": "success", "data": {"participation_id": "...", "status": "applied", "token_used": 30, "token_balance": 130}}
```

## 다이어리 (인증 필요)

### POST /diary/entries
음성 또는 텍스트 일기 등록 (`audio`, `text_content` 중 하나 필수)

> `ai.ai_service.summarize_diary` 연동 전까지는 Mock 감정 요약 반환 (`# TODO: AI 연동 필요`)

**Request**: `multipart/form-data`
- `audio`: 음성 파일 (선택)
- `text_content`: 텍스트 (선택, audio 없을 때)

**Response**
```json
{
  "status": "success",
  "data": {
    "entry_id": "...", "transcript": "...",
    "emotion_summary": {"primary": "평온", "score": {}}, "risk_flag": false, "created_at": "..."
  }
}
```

### GET /diary/entries
일기 목록 조회 (`?limit=10`)

**Response**
```json
{"status": "success", "data": [{"entry_id": "...", "transcript": "...", "emotion_summary": {...}, "created_at": "..."}]}
```

### GET /diary/summary
최근 N일 감정 추이 요약 (`?days=7`)

**Response**
```json
{"status": "success", "data": {"period": "최근 7일", "emotion_trend": [...], "ai_summary": "AI 연동 예정"}}
```

## 지역 프로그램·기관 (인증 필요)

### GET /programs
유저 지역에 맞는 지원 프로그램 목록 조회 (`?region=` 선택, 미입력 시 유저 프로필 region 사용)

**Response**
```json
{"status": "success", "data": [{"program_id": "...", "title": "...", "agency_name": "...", "region": "...", "description": "...", "contact": "...", "apply_url": "..."}]}
```

### POST /programs/{id}/apply
프로그램 관심·연계 이력 기록

**Request**
```json
{"status": "applied"}
```

**Response**
```json
{"status": "success", "data": {"referral_id": "...", "status": "applied"}}
```

## 일일 리포트 (인증 필요)

### GET /reports/daily
오늘(또는 특정 날짜)의 일일 리포트 조회 (`?date=YYYY-MM-DD` 선택)

**Response**
```json
{
  "status": "success",
  "data": {
    "date": "2026-08-13",
    "mission_summary": {"completed": 2, "tokens_earned": 20, "missions": ["...", "..."]},
    "ai_report_text": "오늘 2개의 미션을 완료하고 20토큰을 모았어요."
  }
}
```

## AI 인터페이스 (`ai/ai_service.py`)

백엔드와 AI 파트가 같은 레포를 쓰므로 HTTP 호출 없이 함수를 직접 import해서 사용합니다. 아래 시그니처가 두 파트 간 계약이며, 구현은 AI 파트 담당입니다. 새 함수가 필요하면 이 섹션에 먼저 추가하고 공유해주세요.

### get_mission(level: int, user_type: str) -> dict
레벨/유저 유형에 맞는 미션 추천

**Return**
```json
{"title": "...", "description": "...", "level": 1, "reward_tokens": 10}
```

### summarize_diary(entries: list[str]) -> str
다이어리 엔트리 목록을 요약한 문자열 반환

> 미션 인증 사진 판별(`verify_photo`), 음성 STT(`transcribe_audio`)는 아직 시그니처 미정 — AI 파트 구현 전까지 각 라우터에서 Mock 값으로 대체 중
