"""날짜 찾기·검증.

Phase C에서 Agent Tool(check_date)이 check_date()를 감싸서 쓴다.
"""
import re
from datetime import date

WEEKDAYS = "월화수목금토일"

_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})[-./]\s*(?P<m>\d{1,2})[-./]\s*(?P<d>\d{1,2})"),
    re.compile(r"(?:(?P<y>20\d{2})년\s*)?(?P<m>\d{1,2})월\s*(?P<d>\d{1,2})일"),
    re.compile(r"(?<![\d/])(?P<m>\d{1,2})/(?P<d>\d{1,2})(?![\d/])"),
]

# 날짜로 바꿀 수 없는 모호한 표현 → '확인 필요'
VAGUE_WORDS = ["다음 주", "다음주", "이번 주", "이번주", "주중", "학기 초", "학기초", "월말", "월초", "조만간", "추후"]


def find_dates(text: str, year: int) -> list[dict]:
    """텍스트에서 날짜 표현을 찾아 check_date 결과 목록으로 돌려준다."""
    results, seen = [], set()
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            span = m.span()
            if any(s <= span[0] < e for s, e in seen):
                continue
            seen.add(span)
            results.append(check_date(m.group(0), year))
    return results


def find_vague(text: str) -> list[str]:
    return [w for w in VAGUE_WORDS if w in text]


def check_date(text: str, year: int, today: date | None = None) -> dict:
    """날짜 문자열을 정규화하고 요일·D-day·주말 여부를 계산한다."""
    today = today or date.today()
    for pattern in _PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        y = int(m.group("y")) if m.groupdict().get("y") else year
        try:
            d = date(y, int(m.group("m")), int(m.group("d")))
        except ValueError:
            return {"input": text, "valid": False, "error": "존재하지 않는 날짜"}
        dday = (d - today).days
        return {
            "input": text,
            "valid": True,
            "date": d.isoformat(),
            "weekday": WEEKDAYS[d.weekday()],
            "is_weekend": d.weekday() >= 5,
            "d_day": dday,
            "d_day_label": "D-day" if dday == 0 else (f"D-{dday}" if dday > 0 else f"D+{-dday} (지남)"),
        }
    return {"input": text, "valid": False, "error": "날짜 형식을 찾지 못함"}
