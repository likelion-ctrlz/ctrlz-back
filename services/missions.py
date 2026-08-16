"""자가진단 레벨 ↔ 미션 난이도 범위 매핑. DB 의존성 없는 순수 함수/상수."""

# 난이도 스케일: 1(쉬움) ~ 7(어려움)
# 레벨이 올라갈수록 시작점이 2씩 밀리는 등차 구간 (구간은 서로 겹침 — 인접 레벨끼리 공유되는 미션이 자연스럽게 생김)
LEVEL_DIFFICULTY_MAP = {
    1: (1, 3),
    2: (3, 5),
    3: (4, 6),
    4: (5, 7),
}

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 7


def difficulty_range_for_level(level: int | None) -> tuple[int, int]:
    """자가진단 레벨에 해당하는 (최소, 최대) 난이도 범위. 레벨이 없으면 전체 범위."""
    if level is None:
        return (MIN_DIFFICULTY, MAX_DIFFICULTY)
    return LEVEL_DIFFICULTY_MAP.get(level, (MIN_DIFFICULTY, MAX_DIFFICULTY))


def target_levels_for_difficulty(difficulty: int) -> list[int]:
    """해당 난이도를 추천 범위에 포함하는 자가진단 레벨 목록 (정보 표시/시딩용)."""
    return [lvl for lvl, (lo, hi) in LEVEL_DIFFICULTY_MAP.items() if lo <= difficulty <= hi]
