"""자가진단(8문항, 3축) 점수 계산 로직. DB 의존성 없는 순수 함수."""


def calculate_assessment(answers: list[int]) -> dict:
    """
    answers: [Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8]
    Q1(0~4), Q2(0~3), Q3(0~4), Q4(0~4), Q5(0~3), Q6(0~3), Q7(0~3), Q8(0~3)

    Q1 외출빈도, Q2 두문불출, Q3 지속기간 → 은둔축 (만점 11)
    Q4 오프라인접촉, Q5 관계형태, Q6 지지체계 → 고립축 (만점 10)
    Q7 소속여부, Q8 정서상태 → 심각도축 (만점 6)
    """
    q1, q2, q3, q4, q5, q6, q7, q8 = answers

    # 축별 원점수
    hikikomori_raw = q1 + q2 + q3  # 은둔축, 만점 11
    isolation_raw = q4 + q5 + q6  # 고립축, 만점 10
    severity_raw = q7 + q8  # 심각도축, 만점 6

    # 1단계: 스크리닝 게이트
    gate_score = hikikomori_raw + isolation_raw  # 만점 21
    if gate_score / 21 < 0.42:
        return {
            "assessment_level": 4,
            "assessment_type": "관찰군",
            "assessment_score": round((gate_score / 21) * 10),
            "hikikomori_pct": round(hikikomori_raw / 11 * 100),
            "isolation_pct": round(isolation_raw / 10 * 100),
            "severity_pct": round(severity_raw / 6 * 100),
            "overall_pct": round((gate_score / 21) * 100),
        }

    # 2단계: 축별 비율
    hq_pct = hikikomori_raw / 11 * 100
    si_pct = isolation_raw / 10 * 100
    sv_pct = severity_raw / 6 * 100

    # 유형 판정 (은둔형 조건: 은둔축 ≥42% AND Q3 ≥ 2 — 6개월 이상, 보건복지부 정의)
    is_hikikomori = hq_pct >= 42 and q3 >= 2
    is_isolated = si_pct >= 42

    if is_hikikomori and is_isolated:
        assessment_type = "복합형"
    elif is_hikikomori:
        assessment_type = "은둔형"
    elif is_isolated:
        assessment_type = "고립형"
    else:
        assessment_type = "관찰군"

    # 3단계: 레벨 산정
    overall = (hq_pct + si_pct + sv_pct) / 3
    if overall >= 75:
        level = 1
    elif overall >= 50:
        level = 2
    elif overall >= 25:
        level = 3
    else:
        level = 4

    if assessment_type == "관찰군":
        level = 4

    display_score = round(overall / 10)  # 0~10

    return {
        "assessment_level": level,
        "assessment_type": assessment_type,
        "assessment_score": display_score,
        "hikikomori_pct": round(hq_pct),
        "isolation_pct": round(si_pct),
        "severity_pct": round(sv_pct),
        "overall_pct": round(overall),
    }
