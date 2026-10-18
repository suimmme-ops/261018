"""개인정보 마스킹.

에이전트(LLM)에 텍스트를 보내기 전에 프로그램이 항상 실행한다.
에이전트의 도구가 아니므로 에이전트가 건너뛸 수 없다.
"""
import re

# (라벨, 패턴, 치환 함수)
_RULES = [
    ("주민등록번호", re.compile(r"\b\d{6}\s*-\s*[1-4]\d{6}\b"), lambda m: "●●●●●●-●●●●●●●"),
    ("전화번호", re.compile(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b"), lambda m: "010-●●●●-●●●●"),
    ("전화번호", re.compile(r"\b0\d{1,2}-\d{3,4}-\d{4}\b"), lambda m: "0●●-●●●●-●●●●"),
    ("이메일", re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b"), lambda m: "●●●@●●●"),
    # "담당 김철수", "담당자: 이영희", "문의 박민수"
    (
        "이름",
        re.compile(r"(담당자?|문의|작성자|보고자)(\s*[:：]?\s*)([가-힣]{2,4})(?=[\s,.)]|$)"),
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)[0]}○○",
    ),
    # "김철수 선생님", "이영희 주무관"
    (
        "이름",
        re.compile(r"([가-힣]{2,4})(\s*)(선생님|교사|주무관|부장님|교감|교장)"),
        lambda m: f"{m.group(1)[0]}○○{m.group(2)}{m.group(3)}",
    ),
]


def mask_text(text: str) -> tuple[str, list[dict]]:
    """마스킹한 텍스트와, 무엇을 가렸는지 목록을 돌려준다."""
    found = []
    for label, pattern, repl in _RULES:
        def _sub(m, label=label, repl=repl):
            replaced = repl(m)
            if replaced != m.group(0):
                found.append({"type": label, "original": m.group(0), "masked": replaced})
            return replaced

        text = pattern.sub(_sub, text)
    return text, found
