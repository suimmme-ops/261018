"""샘플 데이터(공문·로드맵) 조회 함수.

Phase C에서 Agent Tool(search_documents, get_roadmap)이 이 함수들을 그대로 감싸서 쓴다.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def load_documents() -> list[dict]:
    with open(DATA_DIR / "documents.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_roadmap() -> dict:
    with open(DATA_DIR / "roadmap.json", encoding="utf-8") as f:
        return json.load(f)


def get_profile() -> dict:
    return load_roadmap()["profile"]


def get_document(doc_id: str) -> dict | None:
    return next((d for d in load_documents() if d["doc_id"] == doc_id), None)


def get_cards(month: int | None = None) -> list[dict]:
    cards = load_roadmap()["cards"]
    if month is None:
        return cards
    return [c for c in cards if c["month"] == month]


def search_documents(keyword: str, month: int | None = None) -> list[dict]:
    """제목·요지·키워드에 검색어가 들어 있는 공문을 찾는다. 공백으로 나눈 단어 중 하나라도 맞으면 포함."""
    words = [w for w in keyword.split() if w]
    results = []
    for doc in load_documents():
        text = " ".join([doc["title"], doc["summary"], *doc["keywords"]])
        if words and not any(w in text for w in words):
            continue
        if month is not None and int(doc["issued"][5:7]) != month:
            continue
        results.append(doc)
    return results
