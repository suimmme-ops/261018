"""Gemini를 OpenAI Agents SDK에서 쓰기 위한 설정.

Gemini는 OpenAI 호환 엔드포인트를 제공하므로, base_url만 바꾼 AsyncOpenAI 클라이언트를
OpenAIChatCompletionsModel에 넣으면 Agent(model=...)로 그대로 쓸 수 있다.

키를 읽는 순서
1. 환경변수 GEMINI_API_KEY  (Codespaces Secrets에 등록하면 자동으로 들어옴)
2. 이 파일 옆의 .streamlit/secrets.toml  (어느 폴더에서 실행하든 같은 파일을 읽음)
"""
import os
import tomllib
from pathlib import Path

from agents import OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.8-flash"
SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def _read_secrets_file() -> dict:
    try:
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def _get_setting(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    value = str(_read_secrets_file().get(name, "")).strip()
    return value or default


def has_api_key() -> bool:
    return bool(_get_setting("GEMINI_API_KEY"))


def model_name() -> str:
    return _get_setting("GEMINI_MODEL", DEFAULT_MODEL)


def diagnose() -> list[str]:
    """키를 어디서 찾았는지/못 찾았는지 설명한다. 키 값은 출력하지 않는다."""
    lines = []
    env = os.environ.get("GEMINI_API_KEY", "").strip()
    lines.append(f"- 환경변수 GEMINI_API_KEY: {'있음' if env else '없음'}")
    if SECRETS_PATH.exists():
        try:
            with open(SECRETS_PATH, "rb") as f:
                data = tomllib.load(f)
            has = bool(str(data.get("GEMINI_API_KEY", "")).strip())
            lines.append(f"- {SECRETS_PATH}: 파일 있음, GEMINI_API_KEY {'있음' if has else '없음'}")
        except tomllib.TOMLDecodeError as e:
            lines.append(f"- {SECRETS_PATH}: 파일 형식 오류 ({e}). 값은 큰따옴표로 감싸야 합니다.")
    else:
        lines.append(f"- {SECRETS_PATH}: 파일 없음")
        others = sorted(p.name for p in SECRETS_PATH.parent.glob("secrets*")) if SECRETS_PATH.parent.exists() else []
        if others:
            lines.append(f"  (같은 폴더에 {', '.join(others)} 이(가) 있습니다. 이름이 정확히 secrets.toml 인지 확인하세요.)")
    return lines


def build_model() -> OpenAIChatCompletionsModel:
    api_key = _get_setting("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY를 찾지 못했습니다.\n" + "\n".join(diagnose()))
    # 트레이싱은 OpenAI 서버로 보내는 기능이라 OpenAI 키가 없으면 끈다.
    set_tracing_disabled(True)
    client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=api_key)
    return OpenAIChatCompletionsModel(model=model_name(), openai_client=client)
