"""에이전트가 쓰는 도구 4종.

- 읽기: search_documents, get_roadmap
- 계산: check_date
- 후보 등록: propose_deadline (확정·삭제·캘린더 등록 도구는 일부러 주지 않는다)

Gemini의 OpenAI 호환 API에서 문제 없도록 매개변수는 선택값(Optional) 없이 단순한 타입만 쓴다.
"""
import json
from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool

import data_store
import dates


@dataclass
class EduContext:
    """Runner.run_sync(context=...)로 넘기는 실행 맥락. 도구와 Instructions가 함께 본다."""
    profile: dict
    proposals: list[dict] = field(default_factory=list)  # 이번 답변에서 올린 기한 후보
    tool_calls: list[str] = field(default_factory=list)  # 화면에 보여 줄 도구 사용 기록


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


@function_tool
def search_documents(ctx: RunContextWrapper[EduContext], keyword: str) -> str:
    """담당 업무와 관련된 공문을 키워드로 검색한다. 공문번호, 제목, 시행일, 연도, 요지를 돌려준다.

    Args:
        keyword: 검색어. 여러 단어는 공백으로 구분한다. 예: "외부강사 채용"
    """
    ctx.context.tool_calls.append(f"search_documents(\"{keyword}\")")
    year = ctx.context.profile["year"]
    docs = data_store.search_documents(keyword)
    results = [
        {
            "doc_id": d["doc_id"],
            "title": d["title"],
            "issued": d["issued"],
            "label": "공식" if d["year"] == year else "전년도 참고",
            "summary": d["summary"],
        }
        for d in docs
    ]
    return _dump(results or {"result": "관련 공문 없음"})


@function_tool
def get_roadmap(ctx: RunContextWrapper[EduContext], month: int) -> str:
    """월별 업무 로드맵 카드를 조회한다. 업무명, 시기, 기한, 상태(공식/참고/확인 필요), 근거 공문번호, 전임자 경험 팁을 돌려준다.

    Args:
        month: 조회할 월(1~12). 연간 전체가 필요하면 0을 넣는다.
    """
    ctx.context.tool_calls.append(f"get_roadmap({month})")
    cards = data_store.get_cards(None if month == 0 else month)
    if not cards:
        return _dump({"result": f"{month}월에 등록된 업무 없음"})
    return _dump([{k: c[k] for k in ("title", "period", "due", "status", "doc_ids", "tip")} for c in cards])


@function_tool
def check_date(ctx: RunContextWrapper[EduContext], date_text: str) -> str:
    """날짜 표현을 YYYY-MM-DD로 바꾸고 요일, 오늘 기준 D-day, 주말 여부를 계산한다. 존재하지 않는 날짜면 오류를 돌려준다.

    Args:
        date_text: 날짜 표현. 예: "10월 23일", "2026-10-23", "10/23"
    """
    ctx.context.tool_calls.append(f"check_date(\"{date_text}\")")
    return _dump(dates.check_date(date_text, ctx.context.profile["year"]))


@function_tool
def propose_deadline(ctx: RunContextWrapper[EduContext], task: str, date: str, source: str) -> str:
    """교사가 확인할 '확인 대기 기한' 목록에 기한 후보를 1건 올린다. 확정이 아니며, 확정은 교사가 화면에서 한다.

    Args:
        task: 업무명. 예: "만족도 조사 결과 요약 제출"
        date: check_date로 확인한 YYYY-MM-DD 날짜
        source: 근거. 공문번호 또는 "업무 메시지 (공문번호 미확인)"
    """
    ctx.context.tool_calls.append(f"propose_deadline(\"{task}\", \"{date}\")")
    checked = dates.check_date(date, ctx.context.profile["year"])
    if not checked["valid"]:
        return _dump({"ok": False, "error": checked["error"]})
    ctx.context.proposals.append({"task": task, "date": checked["date"], "source": source})
    return _dump({"ok": True, "message": "확인 대기 목록에 올렸습니다. 교사의 확정이 필요합니다."})


ALL_TOOLS = [search_documents, get_roadmap, check_date, propose_deadline]
