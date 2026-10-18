"""Phase A용 가짜(규칙 기반) 응답기.

Phase B에서 mock_reply()를 Agent + Runner 호출로 바꾼다.
화면(app.py)은 reply(답변 마크다운)와 proposals(확인 대기 후보)만 받으므로
응답기만 바꾸면 화면 코드는 그대로 쓸 수 있다.
"""
import re
from datetime import date

import data_store
import dates

_MONTH_ONLY = re.compile(r"(\d{1,2})월(?!\s*\d{1,2}일)")
_STOPWORDS = {"뭐", "뭐야", "뭐예요", "언제", "어떻게", "해요", "해야", "하나요", "있나요", "알려줘", "알려주세요", "부터", "까지", "관련", "업무",
              "공문", "있어요", "일정", "작년", "올해", "알려줘요", "방과후", "방과후학교"}


def _doc_line(doc_id: str) -> str:
    doc = data_store.get_document(doc_id)
    if not doc:
        return doc_id
    return f"`{doc_id}` {doc['title']}"


def _card_block(card: dict) -> str:
    lines = [f"- **{card['title']}** — {card['period']} · _{card['status']}_"]
    for doc_id in card["doc_ids"]:
        lines.append(f"  - 근거: {_doc_line(doc_id)}")
    if not card["doc_ids"]:
        lines.append("  - 근거: 공문 없음 (전임자 경험 기반)")
    if card["tip"]:
        lines.append(f"  - 💡 경험 팁: {card['tip']}")
    return "\n".join(lines)


def _guess_task(text: str) -> str:
    """메시지와 가장 많이 겹치는 로드맵 업무명을 고른다. 없으면 메시지 앞부분."""
    best, best_score = None, 0
    for card in data_store.get_cards():
        score = sum(1 for w in card["title"].replace("·", " ").split() if len(w) >= 2 and w in text)
        if score > best_score:
            best, best_score = card["title"], score
    if best:
        return best
    first = re.split(r"[.\n!?]", text.strip())[0]
    return first[:30] or "메시지 업무"


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z]{2,}", text)
    return [w for w in words if w not in _STOPWORDS]


def mock_reply(text: str, profile: dict, today: date | None = None) -> tuple[str, list[dict]]:
    today = today or date.today()
    year = profile["year"]

    # 1) 메시지 분석: 날짜 표현이 있거나 모호한 기한 표현이 있는 경우
    found = [d for d in dates.find_dates(text, year) if d["valid"]]
    vague = dates.find_vague(text)
    if found or vague:
        task = _guess_task(text)
        if not found:
            reply = (
                f"메시지에서 **{task}** 관련 할 일을 찾았습니다.\n\n"
                f"그런데 기한이 \"{vague[0]}\"처럼 모호하게 적혀 있어 날짜를 정할 수 없습니다. "
                "**정확한 제출일이 언제인지** 알려 주시겠어요? (예: 10월 23일)"
            )
            return reply, []
        proposals, lines = [], []
        for d in found:
            weekend = " ⚠️ 주말" if d["is_weekend"] else ""
            lines.append(f"- {d['date']} ({d['weekday']}) · {d['d_day_label']}{weekend}")
            proposals.append({"task": task, "date": d["date"], "source": "업무 메시지 (공문번호 미확인)"})
        reply = (
            f"메시지에서 **{task}** 관련 기한을 찾았습니다.\n\n"
            + "\n".join(lines)
            + "\n\n아래 **확인 대기 기한**에 올려 두었습니다. 원문과 대조한 뒤 직접 확정해 주세요. "
            "공문번호가 있으면 함께 확인하는 것이 좋습니다."
        )
        return reply, proposals

    # 2) 월별 할 일: "3월", "이번 달"
    month = None
    if "이번 달" in text or "이번달" in text:
        month = today.month
    elif "다음 달" in text or "다음달" in text:
        month = today.month % 12 + 1
    elif m := _MONTH_ONLY.search(text):
        month = int(m.group(1))
    if month and 1 <= month <= 12:
        cards = data_store.get_cards(month)
        if not cards:
            return (
                f"{month}월에 등록된 {profile['task_keyword']} 업무가 없습니다. "
                "앞뒤 달 업무를 확인하거나, 받은 공문이 있다면 업로드해 주세요.",
                [],
            )
        reply = (
            f"**{month}월 {profile['task_keyword']} 할 일** ({len(cards)}건)\n\n"
            + "\n".join(_card_block(c) for c in cards)
            + "\n\n이 중 이미 끝낸 업무가 있나요? 로드맵 탭에서 완료 체크할 수 있습니다."
        )
        return reply, []

    # 3) 공문 검색
    words = _keywords(text)
    docs = data_store.search_documents(" ".join(words)) if words else []
    if not docs:
        return (
            "관련 공문을 찾지 못했습니다. **확인 필요** 항목입니다.\n\n"
            "- 업무관리시스템에서 공문을 검색하거나 받은 공문을 업로드해 주세요.\n"
            "- 전년도 담당자나 부장님께 시기를 확인하는 방법도 있습니다.\n\n"
            "_근거 없이 날짜를 추측하지 않습니다._",
            [],
        )
    lines = []
    for doc in docs[:4]:
        tag = "공식" if doc["year"] == year else "전년도 참고"
        lines.append(f"- `{doc['doc_id']}` **{doc['title']}** ({doc['issued']} 시행 · _{tag}_)\n  - {doc['summary']}")
    reply = f"관련 공문 {len(docs)}건을 찾았습니다.\n\n" + "\n".join(lines)
    return reply, []
