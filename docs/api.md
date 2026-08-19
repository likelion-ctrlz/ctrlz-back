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
닉네임을 받아 유저 생성 + 세션 토큰 발급 (온보딩). `DEMO_NICKNAMES` 환경변수에 등록된 닉네임이면 `is_demo=true`로 생성됩니다.

**Request**
```json
{"nickname": "숲속고양이"}
```

**Response**
```json
{
  "status": "success",
  "data": {"session_token": "abc123...", "user_id": "...", "nickname": "숲속고양이", "is_demo": false}
}
```

### DELETE /session
로그아웃. `Authorization: Bearer {session_token}` 헤더로 넘어온 세션을 삭제합니다.
이미 만료·삭제된 토큰이어도 에러 없이 성공 처리됩니다.

**Response**
```json
{
  "status": "success",
  "data": {"message": "로그아웃되었습니다"}
}
```

## 사용자 (인증 필요)

### GET /users/me
홈 화면용 엔드포인트. 닉네임·지역·자가진단 결과·캐릭터(모로) 상태·연속 기록일·토큰 잔액·오늘의 추천 미션까지 한 번에 반환합니다.

**Response**
```json
{
  "status": "success",
  "data": {
    "user_id": "...", "nickname": "숲속고양이", "region": "서울 마포구", "is_demo": false,

    "assessment_level": 2, "assessment_type": "은둔형", "assessment_score": 6,

    "character_level": 2, "character_xp": 40, "character_xp_next_level": 30,
    "character_image": "baby_morro",

    "mission_streak_days": 3,

    "token_balance": 150,

    "today_recommended_mission": {
      "mission_id": "...", "title": "산책하면서 길고양이 찾아서 사진찍기", "description": "혹시 알아요? 오늘 당신에게 행운이 찾아올지",
      "token_reward": 20, "xp_reward": 20, "difficulty": 3
    }
  }
}
```

- `character_image`: `egg`(1) → `baby_morro`(2) → `kid_morro`(3) → `morro`(4)
- `character_xp_next_level`: 다음 레벨까지 남은 XP. 최고 레벨(4)이면 0
- `mission_streak_days`: 연속으로 미션을 인증(approved)한 일수. 오늘 아직 안 했어도 어제까지 이어져 있으면 유지됨(자정 넘자마자 0으로 끊기지 않도록 하루 유예)
- `today_recommended_mission`: 오늘 날짜 기준으로 결정론적으로 뽑힌 추천 미션 1개(같은 유저는 하루 동안 새로고침해도 동일). 후보가 없으면 `null`

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

8문항, 3개 축(은둔축/고립축/심각도축)으로 구성. 상세 채점 로직은 `services/assessment.py` 참고.

### POST /assessment/submit
설문 응답 제출 → 위험 수준(레벨 1~4)·유형(관찰군/은둔형/고립형/복합형) 산출 후 `users` 테이블에 저장 (재제출 시 덮어씀)

**Request**
```json
{"answers": [3, 2, 2, 3, 2, 2, 2, 1]}
```
`answers` 순서: `[1.외출빈도(0~4), 2.두문불출(0~3), 3.지속기간(0~4), 4.오프라인접촉(0~4), 5.관계형태(0~3), 6.지지체계(0~3), 7.소속여부(0~3), 8.정서상태(0~3)]`

**Response**
```json
{
  "status": "success",
  "data": {
    "assessment_level": 2, "assessment_type": "은둔형", "assessment_score": 6,
    "hikikomori_pct": 55, "isolation_pct": 40, "severity_pct": 50, "overall_pct": 48,
    "description": "..."
  }
}
```

### GET /assessment/result
가장 최근 자가진단 결과 조회. 제출 이력이 없으면 404.

**Response**
```json
{"status": "success", "data": {"assessment_level": 2, "assessment_type": "은둔형", "assessment_score": 6, "assessed_at": "..."}}
```

## 미션 (인증 필요)

난이도 스케일은 1(쉬움)~7(어려움). 자가진단 레벨별 추천 범위: 레벨1→1~3 / 레벨2→3~5 / 레벨3→4~6 / 레벨4→5~7 (인접 레벨끼리 겹침).

### GET /missions/recommended
자가진단 레벨에 맞는 난이도 범위의 미션 목록 조회 (`?limit=5`). 오늘 이미 승인된 미션은 제외. 데모 유저는 자가진단 레벨/난이도와 무관하게 `is_wow=true` 미션만 노출.

**Response**
```json
{
  "status": "success",
  "data": [
    {
      "mission_id": "...", "title": "창문 열고 3분 바람 쐬기", "description": "...",
      "difficulty": 3, "category": "외출", "verification_type": "photo",
      "xp_reward": 10, "token_reward": 20, "bonus_token": 0, "is_wow": false
    }
  ]
}
```

### GET /missions/{id}
미션 상세(긴 설명·인증 조건 체크리스트·보상 정보) 조회

**Response**
```json
{
  "status": "success",
  "data": {
    "mission_id": "...", "title": "...", "description": "...", "detail_description": "...",
    "difficulty": 3, "difficulty_label": "중하", "category": "외출", "verification_type": "photo",
    "conditions": ["야외에서 촬영한 사진이어야 해요", "..."],
    "xp_reward": 20, "token_reward": 20, "bonus_token": 0, "is_wow": false
  }
}
```

### POST /missions/{id}/submit
미션 인증 사진 업로드 → AI(GPT-4o-mini Vision) 판별 → 통과 시 XP·토큰 즉시 지급 + 캐릭터 레벨업 체크.
미션 승인 1건당 XP 임계값과 무관하게 캐릭터가 무조건 1레벨 오릅니다(MAX_LEVEL=4에서 정지, 전체 유저 공통).
오늘 완료로 연속 인증일(streak, 오늘 포함)이 3의 배수가 되면 이번 완료의 XP·토큰에 50% 보너스가 붙습니다.

**Request**: `multipart/form-data`
- `photo`: 이미지 파일
- `taken_at`: ISO datetime

**Response**
```json
{
  "status": "success",
  "data": {
    "completion_id": "...", "ai_verdict": true, "ai_feedback": "잘 하셨어요!",
    "xp_earned": 20, "token_earned": 25, "bonus_token": 5, "streak_bonus_applied": false,
    "character_level_before": 1, "character_level_after": 2, "character_xp": 20,
    "leveled_up": true, "character_image": "baby_morro", "next_level_xp": 10,
    "token_balance": 160
  }
}
```
`bonus_token`은 미션별로 고정된 와우포인트 보너스(연속일과 무관), `streak_bonus_applied`는 이번 완료가 연속 3일째(의 배수)라 XP·토큰에 50%가 곱해졌는지 여부입니다. 두 보너스는 독립적으로 함께 적용될 수 있습니다.
실패(`ai_verdict=false`) 시 `status="rejected"`로 저장되고 보상 관련 필드는 대부분 `null`/0입니다.

### GET /missions/{id}/result
특정 미션의 가장 최근 인증 시도 결과 조회 (폴링용). 인증 이력 없으면 404.

**Response**
```json
{"status": "success", "data": {"completion_id": "...", "status": "approved", "ai_verdict": true, "ai_feedback": "...", "xp_earned": 20, "token_earned": 25, "photo_url": "https://..."}}
```

### GET /missions/history
미션 완료 이력 조회 (`?date=YYYY-MM-DD` 선택)

**Response**
```json
{"status": "success", "data": [{"completion_id": "...", "mission_id": "...", "mission_title": "...", "status": "approved", "xp_earned": 20, "token_earned": 25, "completed_at": "..."}]}
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
자가진단 레벨에 맞는 취미활동 목록 조회. DB에 매칭 데이터가 없으면 에버러닝 공공API(실패 시 큐레이션 더미)로 채워서 저장 후 반환.

**Response**
```json
{
  "status": "success",
  "data": [
    {
      "hobby_id": "...", "title": "실내 원예 모임", "description": "...", "category": "원예",
      "tags": ["원예", "실내", "초보 환영"], "difficulty": "초급",
      "image_url": "https://images.unsplash.com/photo-...", "token_cost": 30
    }
  ]
}
```
`difficulty`는 `"초급"|"중급"|"고급"`. `image_url`은 임시 목데이터 사진(Unsplash) — 실제 강좌 사진 연동 전까지 사용하며, 외부 API로 채워진 항목은 실제 사진을 알 수 없어 `null`일 수 있습니다.

### GET /hobbies/{id}
취미활동 상세 조회. 목록 카드 필드에 더해 일정·장소·소요시간·정원·부담 수준·참여 조건까지 반환합니다. 없으면 404.

**Response**
```json
{
  "status": "success",
  "data": {
    "hobby_id": "...", "title": "도자기 공방 체험", "description": "...", "category": "공예",
    "tags": ["공예", "실내", "초보 환영"], "difficulty": "초급", "image_url": "https://...",
    "token_cost": 40,
    "detail_description": "손으로 흙을 빚으며 집중과 이완을 동시에 경험할 수 있는 클래스예요.\n별도 경험이 없어도 강사가 처음부터 함께 도와드려요.",
    "schedule": "매주 목요일 오후 2시", "location": "서울 마포구 모로 공방 스튜디오",
    "duration": "약 2시간", "capacity": "최대 8명 (소규모로 진행)",
    "physical_burden": "낮음", "social_burden": "소규모", "preparation_burden": "없음",
    "conditions": ["재료비 포함, 별도 준비물 없어요", "참여 취소는 하루 전까지 가능해요", "사진 촬영은 자유이며 공유 의무는 없어요"]
  }
}
```
`*_burden`(신체 활동/사회적 상호작용/사전 준비)과 `schedule`/`location`/`duration`/`capacity`/`conditions`는 에버러닝 API로 자동 채워진 항목(상세 정보를 알 수 없는 경우)에서는 `null`/`[]`일 수 있습니다 — 억지로 채우지 않고 정직하게 비워둡니다.

### POST /hobbies/{id}/apply
토큰을 사용해 취미활동 참여 신청

**Response**
```json
{"status": "success", "data": {"participation_id": "...", "status": "applied", "token_used": 30, "token_balance": 130}}
```

## 다이어리 (인증 필요)

### POST /diary/entries
음성 또는 텍스트 일기 등록 (`audio`, `text_content` 중 하나 필수). 음성은 Whisper STT + GPT 감정분석까지 자동 처리되고, `risk_level`이 2(자기위해 신호)면 `risk_flag=true`로 저장됩니다.

**Request**: `multipart/form-data`
- `audio`: 음성 파일 (선택)
- `text_content`: 텍스트 (선택, audio 없을 때 사실상 필수)

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
{
  "status": "success",
  "data": {
    "period": "최근 7일",
    "emotion_trend": [{"date": "2026-08-11", "primary": "편안함"}, {"date": "2026-08-12", "primary": "무기력"}],
    "most_frequent_emotion": "무기력",
    "emotion_percentages": {"편안함": 57, "무기력": 43},
    "ai_summary": "이번 주에는 바깥 공기를 쐰 날이 늘었어요. 작지만 분명한 변화예요.",
    "pattern": {"emotion": "무기력", "time_slot": "저녁", "count": 3, "pattern_text": "'무기력' 감정이 주로 저녁 시간대에 많이 기록됐어요"}
  }
}
```
`pattern`은 감정 기록이 3건 미만이면 `null`.
`most_frequent_emotion`/`emotion_percentages`는 조회 기간 내 일기가 하나도 없으면 각각 `null`/`{}`. "지난 주 대비" 같은 기간 비교 문구는 아직 없고 `ai_summary`(AI 생성)로만 변화를 짚어줍니다.

## 지역 프로그램·기관 (인증 필요)

### GET /programs
유저 지역에 맞는 지원 프로그램 목록 조회 (`?region=` 선택, 미입력 시 유저 프로필 region 사용). DB에 매칭 데이터가 없으면 에버러닝 공공API(실패 시 큐레이션 더미)로 채워서 저장 후 반환.

**Response**
```json
{"status": "success", "data": [{"program_id": "...", "title": "...", "agency_name": "...", "region": "...", "description": "...", "contact": "...", "apply_url": "..."}]}
```

### POST /programs/{id}/apply
프로그램 관심·연계 이력 기록 (실제 신청은 `apply_url`로 이동해서 이뤄짐)

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
오늘(또는 특정 날짜)의 일일 리포트 조회 (`?date=YYYY-MM-DD` 선택). 하루에 한 번만 생성되고 이후엔 캐시처럼 재사용됩니다. `ai_report_text`는 현재 AI가 아니라 템플릿 문자열로 생성됩니다.

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

백엔드와 AI 파트가 같은 레포를 쓰므로 HTTP 호출 없이 함수를 직접 import해서 사용합니다. `OPENAI_API_KEY`가 없거나 호출이 실패하면 자동으로 더미 응답으로 폴백하므로, 백엔드/프론트는 AI 상태와 무관하게 항상 정상 응답을 받습니다.

### get_missions(level: int, user_type: str | None, count: int = 3) -> list[dict]
레벨에 맞는 미션 추천 목록 (LLM 미사용 — 재현성을 위해 고정 풀에서 선택)

### verify_photo(image_bytes: bytes, mission_title: str) -> dict
미션 인증 사진 판별 (GPT-4o-mini Vision). `{"passed": bool, "confidence": float, "comment": str}` 반환. 실패 판정을 최소화하도록 설계됨.

### transcribe_diary(audio_bytes: bytes, filename: str) -> dict
음성 일기 STT + 감정분석 (Whisper + GPT). `{"text": str, "emotion": str, "risk_level": 0~2}` 반환.

### summarize_diary(entries: list) -> dict
다이어리 엔트리 목록을 요약 + 감정 추이 반환. `{"summary": str, "trend": [{"date": str, "emotion": str}, ...]}`.
