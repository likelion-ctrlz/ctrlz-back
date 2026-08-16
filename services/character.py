"""캐릭터(모로) 레벨업 로직. DB 의존성 없는 순수 함수.

[레벨업 규칙 — 전원 공통]
행사 현장 참여자 포함 전체 유저 대상으로, 미션을 하나 완료(승인)할 때마다
XP 임계값과 무관하게 무조건 character_level += 1 (MAX_LEVEL=4에서 정지).
XP는 계속 누적되어 진행률 표시(next_level_xp)에만 쓰인다.
"""

XP_THRESHOLDS = [0, 30, 70, 120]
# 인덱스 = level-1, 값 = 해당 레벨의 "기준" 누적 XP (레벨업 게이팅에는 더 이상 쓰이지 않음, 진행률 표시용)

CHARACTER_STAGES = {
    1: {"name": "알", "image": "egg"},
    2: {"name": "아기 모로", "image": "baby_morro"},
    3: {"name": "꼬마 모로", "image": "kid_morro"},
    4: {"name": "모로", "image": "morro"},
}

MAX_LEVEL = 4


def check_level_up(current_level: int, current_xp: int, added_xp: int) -> dict:
    """
    미션 완료 1회 = 무조건 레벨업 1단계 (MAX_LEVEL에서 정지). 전체 유저 공통 규칙.

    Returns:
        new_level, new_xp, leveled_up (bool), character_image, character_name, next_level_xp
    """
    new_xp = current_xp + added_xp
    new_level = min(current_level + 1, MAX_LEVEL)
    leveled_up = new_level > current_level

    next_threshold = XP_THRESHOLDS[new_level] if new_level < MAX_LEVEL else None
    next_level_xp = next_threshold - new_xp if next_threshold is not None else 0
    # level 4가 최대 — next_level_xp=0이면 프론트에서 "최고 레벨" 표시

    return {
        "new_level": new_level,
        "new_xp": new_xp,
        "leveled_up": leveled_up,
        "character_image": CHARACTER_STAGES[new_level]["image"],
        "character_name": CHARACTER_STAGES[new_level]["name"],
        "next_level_xp": max(next_level_xp, 0),
    }
