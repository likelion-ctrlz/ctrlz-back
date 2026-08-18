-- 지역연계 프로그램 카드에 사진을 보여주기 위한 컬럼 추가
--
-- 대상: programs
-- 두 번 실행해도 안전하도록(idempotent) 작성됨.
--
-- 실행 예: psql "$DATABASE_URL" -f migrations/003_program_image.sql

BEGIN;

ALTER TABLE programs
    ADD COLUMN IF NOT EXISTS image_url text;

COMMIT;
