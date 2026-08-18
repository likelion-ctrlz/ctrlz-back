"""일기 감정 추이 통계 계산. DB 의존성 없는 순수 함수."""

from collections import Counter


def compute_emotion_stats(trend: list[dict]) -> dict:
    """감정 추이(trend)에서 감정별 비율과 가장 자주 기록된 감정을 계산.

    Args:
        trend: [{"date": str, "emotion": str}, ...] — ai_service.summarize_diary()의 trend

    Returns:
        {"most_frequent_emotion": str | None, "emotion_percentages": {emotion: 0~100}}
    """
    emotions = [t["emotion"] for t in trend if t.get("emotion")]
    if not emotions:
        return {"most_frequent_emotion": None, "emotion_percentages": {}}

    counts = Counter(emotions)
    total = len(emotions)
    percentages = {emotion: round(count / total * 100) for emotion, count in counts.items()}
    most_frequent_emotion = counts.most_common(1)[0][0]

    return {"most_frequent_emotion": most_frequent_emotion, "emotion_percentages": percentages}
