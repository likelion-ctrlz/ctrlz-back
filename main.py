from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine
from routers import assessment, diary, hobbies, missions, programs, reports, session, tokens, users
from seed_hobbies import seed as seed_hobbies_data
from seed_missions import seed as seed_missions_data
from seed_programs import seed as seed_programs_data

Base.metadata.create_all(bind=engine)

# 앱 시작 시 목데이터 자동 시딩. 세 스크립트 모두 테이블에 데이터가 이미 있으면
# 스킵하는 가드가 있어(seed_*.py 참고) DB를 새로 바꾸거나 재배포해도 안전하게 매번 실행 가능.
seed_missions_data()
seed_hobbies_data()
seed_programs_data()

app = FastAPI(
    title="ctrlz Backend API",
    description=(
        "고립·은둔 청년 자립 지원 서비스 ctrlz의 백엔드 API입니다.\n\n"
        "**인증 방식**: 소셜 로그인 없이 닉네임만으로 `POST /session`을 호출하면 "
        "`session_token`이 발급됩니다. 이후 인증이 필요한 모든 요청의 헤더에 "
        "`Authorization: Bearer {session_token}`을 포함해주세요.\n\n"
        "**응답 형식**: 모든 엔드포인트는 성공 시 `{\"status\": \"success\", \"data\": {...}}`, "
        "실패 시 `{\"status\": \"error\", \"message\": \"...\"}` 형태로 응답합니다."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "session", "description": "닉네임 온보딩으로 세션(로그인) 발급/해제. 인증 불필요."},
        {"name": "users", "description": "내 프로필 조회/수정. 인증 필요."},
        {"name": "assessment", "description": "자가진단 설문 제출 및 결과 조회. 인증 필요."},
        {"name": "missions", "description": "추천 미션 조회, 사진 인증 제출, 인증 이력 조회. 인증 필요."},
        {"name": "tokens", "description": "토큰 지갑 잔액/적립·사용 내역 조회. 인증 필요."},
        {"name": "hobbies", "description": "추천 취미활동 조회 및 토큰으로 참여 신청. 인증 필요."},
        {"name": "diary", "description": "말하는 일기장 등록(음성/텍스트), 목록·감정 추이 조회. 인증 필요."},
        {"name": "programs", "description": "지역 지원 프로그램·기관 조회 및 신청 이력 기록. 인증 필요."},
        {"name": "reports", "description": "일일 미션 수행 요약 및 AI 리포트 조회. 인증 필요."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 배포 시 프론트 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "요청 형식이 올바르지 않습니다"},
    )


app.include_router(session.router)
app.include_router(users.router)
app.include_router(assessment.router)
app.include_router(missions.router)
app.include_router(tokens.router)
app.include_router(hobbies.router)
app.include_router(diary.router)
app.include_router(programs.router)
app.include_router(reports.router)


@app.get("/", summary="헬스 체크", description="서버가 살아있는지 확인용. Railway 슬립 방지를 위해 발표 전 한 번 호출해두세요.")
def health_check():
    return {"status": "success", "data": {"message": "ok"}}
