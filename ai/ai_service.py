# AI 파트 구현 영역. routers/에서 직접 import 해서 사용.
# 아래 함수 시그니처가 백엔드 ↔ AI 간 인터페이스. 구현은 AI 파트 담당.


def get_mission(level: int, user_type: str) -> dict:
    """레벨/유저 유형에 맞는 미션 추천. {"title", "description", "level", "reward_tokens"} 반환"""
    raise NotImplementedError


def summarize_diary(entries: list[str]) -> str:
    """다이어리 엔트리 목록을 요약한 문자열 반환"""
    raise NotImplementedError
