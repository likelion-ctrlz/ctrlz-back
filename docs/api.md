# API 명세

모든 응답은 아래 형식을 따릅니다.

```json
// 성공
{"status": "success", "data": {}}

// 실패
{"status": "error", "message": "에러 메시지"}
```

인증이 필요한 엔드포인트는 `Authorization: Bearer {access_token}` 헤더가 필요합니다.

## 인증

### POST /auth/kakao
카카오 액세스 토큰으로 로그인/가입 후 JWT 발급

**Request**
```json
{"access_token": "카카오 SDK에서 받은 액세스 토큰"}
```

**Response**
```json
{"status": "success", "data": {"access_token": "jwt...", "token_type": "bearer"}}
```

### POST /auth/google
구글 ID 토큰으로 로그인/가입 후 JWT 발급

**Request**
```json
{"id_token": "구글 SDK에서 받은 ID 토큰"}
```

**Response**
```json
{"status": "success", "data": {"access_token": "jwt...", "token_type": "bearer"}}
```

## 미션 (인증 필요)

### GET /missions/recommended
사용자 유형에 맞는 추천 미션 목록 조회

> AI 연동 방식 확정 전까지 user_type 기준 DB 조회로 대체 (`# TODO: AI 연동 필요`)

**Response**
```json
{
  "status": "success",
  "data": [
    {"id": 1, "title": "...", "description": "...", "level": 1, "reward_tokens": 10}
  ]
}
```

### POST /missions/{id}/submit
미션 제출 및 토큰 보상 지급

**Request**
```json
{"content": "제출 내용 (선택)"}
```

**Response**
```json
{
  "status": "success",
  "data": {"submission_id": 1, "reward_tokens": 10, "token_balance": 30}
}
```

## 다이어리 (인증 필요)

### POST /diary/entries
다이어리 작성

**Request**
```json
{"content": "오늘의 기록", "mood": "good"}
```

**Response**
```json
{"status": "success", "data": {"id": 1, "content": "오늘의 기록", "mood": "good"}}
```

### GET /diary/summary
다이어리 요약 조회

> AI 연동 방식 확정 전까지 Mock 값 반환 (`# TODO: AI 연동 필요`)

**Response**
```json
{"status": "success", "data": {"entry_count": 5, "summary": "AI 연동 전 Mock 요약입니다."}}
```

## 토큰 (인증 필요)

### GET /tokens/balance
보유 토큰 잔액 조회

**Response**
```json
{"status": "success", "data": {"token_balance": 30}}
```
