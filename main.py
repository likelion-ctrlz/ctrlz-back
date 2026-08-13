from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine
from routers import assessment, diary, hobbies, missions, programs, reports, session, tokens, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Backend API")

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


@app.get("/")
def health_check():
    return {"status": "success", "data": {"message": "ok"}}
