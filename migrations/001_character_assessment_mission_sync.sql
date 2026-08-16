-- 기획 변경 반영: 자가진단 8문항 체계 + 캐릭터(모로) 시스템 + 미션 XP·와우포인트 확장
--
-- 대상: users, missions, mission_completions
-- 실행 전 스테이징에서 먼저 검증 권장. 두 번 실행해도 안전하도록(idempotent) 작성됨.
--
-- 실행 예: psql "$DATABASE_URL" -f migrations/001_character_assessment_mission_sync.sql

BEGIN;

-- ── users ────────────────────────────────────────────────────────────
-- 기존 status_level → assessment_level, user_type → assessment_type로 리네임 (데이터 보존)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'status_level'
    ) THEN
        ALTER TABLE users RENAME COLUMN status_level TO assessment_level;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'user_type'
    ) THEN
        ALTER TABLE users RENAME COLUMN user_type TO assessment_type;
    END IF;
END $$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_demo          boolean     NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS assessment_score integer,
    ADD COLUMN IF NOT EXISTS assessed_at      timestamptz,
    ADD COLUMN IF NOT EXISTS character_level  integer     NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS character_xp     integer     NOT NULL DEFAULT 0;

-- ── missions ─────────────────────────────────────────────────────────
ALTER TABLE missions
    ADD COLUMN IF NOT EXISTS detail_description text,
    ADD COLUMN IF NOT EXISTS conditions          text[],
    ADD COLUMN IF NOT EXISTS xp_reward           integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS bonus_token         integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_wow              boolean NOT NULL DEFAULT false;

-- ── mission_completions ─────────────────────────────────────────────
ALTER TABLE mission_completions
    ADD COLUMN IF NOT EXISTS xp_earned integer NOT NULL DEFAULT 0;

COMMIT;

-- ────────────────────────────────────────────────────────────────────
-- [선택] 기존 더미 미션(창문 열기 등 10개) 초기화 후 PM 확정 미션 12개로 교체
--
-- ⚠️ 주의: mission_completions까지 함께 비워지므로 지금까지 쌓인 미션 인증 이력이 사라집니다.
-- 데모/테스트 데이터라 상관없다면 아래 주석을 해제해서 별도로 실행하세요.
-- 실행 후 `python seed_missions.py`를 돌리면 PM 목록 12개가 새로 들어갑니다.
--
-- TRUNCATE TABLE mission_completions, missions CASCADE;
