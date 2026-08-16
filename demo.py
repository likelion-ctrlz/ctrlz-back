import os


def is_demo_nickname(nickname: str) -> bool:
    """DEMO_NICKNAMES 환경변수(쉼표 구분)에 포함된 닉네임인지 판별."""
    raw = os.getenv("DEMO_NICKNAMES", "")
    demo_nicknames = {n.strip() for n in raw.split(",") if n.strip()}
    return nickname in demo_nicknames
