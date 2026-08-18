-- 취미활동 상세 페이지(ProgramDetail.jsx)에 필요한 컬럼 추가:
-- 목록 카드용 난이도·임시 사진 + 상세 페이지용 태그·일정·부담 수준·참여 조건
--
-- 대상: hobby_activities
-- 실행 전 스테이징에서 먼저 검증 권장. 두 번 실행해도 안전하도록(idempotent) 작성됨.
--
-- 실행 예: psql "$DATABASE_URL" -f migrations/002_hobby_difficulty_image.sql

BEGIN;

ALTER TABLE hobby_activities
    ADD COLUMN IF NOT EXISTS difficulty          text        NOT NULL DEFAULT '초급',
    ADD COLUMN IF NOT EXISTS image_url           text,
    ADD COLUMN IF NOT EXISTS detail_description  text,
    ADD COLUMN IF NOT EXISTS tags                text[],
    ADD COLUMN IF NOT EXISTS schedule            text,
    ADD COLUMN IF NOT EXISTS location            text,
    ADD COLUMN IF NOT EXISTS duration            text,
    ADD COLUMN IF NOT EXISTS capacity            text,
    ADD COLUMN IF NOT EXISTS physical_burden     text,
    ADD COLUMN IF NOT EXISTS social_burden       text,
    ADD COLUMN IF NOT EXISTS preparation_burden  text,
    ADD COLUMN IF NOT EXISTS conditions          text[];

COMMIT;
