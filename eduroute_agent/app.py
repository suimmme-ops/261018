import uuid
from datetime import date
from pathlib import Path

import streamlit as st
from agents import Runner, SQLiteSession

import data_store
import llm_config
from agent_setup import build_agent
from masking import mask_text
from responder import mock_reply
from tools import EduContext

DB_PATH = str(Path(__file__).parent / "eduroute_agent.db")

# 1. Streamlit 페이지 설정 #
st.set_page_config(page_title="에듀루트 업무 길잡이", page_icon="🧭", layout="wide")

STATUS_BADGE = {"공식": "🟢 공식", "참고": "🟡 전년도 참고", "확인 필요": "🔴 확인 필요"}
profile = data_store.get_profile()

# 2. Session State 초기화 #
defaults = {
    "messages": [],   # 채팅 기록 [{role, content, masked?}]
    "done": set(),    # 완료 체크한 card_id
    "pending": [],    # 확인 대기 기한 [{id, task, date, source}]
    "confirmed": [],  # 교사가 확정한 기한
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def new_agent_session() -> SQLiteSession:
    """에이전트가 대화를 기억하기 위한 멀티턴 세션. 브라우저 세션마다 따로 만든다."""
    return SQLiteSession(f"teacher_{uuid.uuid4().hex[:8]}", DB_PATH)


if "agent_session" not in st.session_state:
    st.session_state.agent_session = new_agent_session()


@st.cache_resource
def get_agent():
    return build_agent()


def ask_agent(text: str, agent_profile: dict) -> tuple[str, list[dict], list[str]]:
    """싱글 에이전트 실행. 답변, 기한 후보, 사용한 도구 목록을 돌려준다."""
    context = EduContext(profile=agent_profile)
    result = Runner.run_sync(get_agent(), text, context=context, session=st.session_state.agent_session)
    return result.final_output, context.proposals, context.tool_calls


def add_pending(task: str, due: str, source: str) -> None:
    exists = any(p["task"] == task and p["date"] == due for p in st.session_state.pending)
    if not exists:
        st.session_state.pending.append({"id": uuid.uuid4().hex[:8], "task": task, "date": due, "source": source})


# 3. 사이드바 #
with st.sidebar:
    st.header("내 업무 선택")
    school_level = st.selectbox("학교급", ["중학교", "초등학교", "고등학교"])
    region = st.selectbox("지역", ["서울", "경기", "부산"])
    office = st.selectbox("교육지원청", ["샘플교육지원청"])
    task_keyword = st.selectbox("업무", ["방과후학교"])
    selected = {"school_level": school_level, "region": region, "office": office, "task_keyword": task_keyword}
    if any(selected[k] != profile[k] for k in selected):
        st.warning("데모 데이터는 '중학교 · 서울 · 방과후학교'만 있습니다. 해당 자료로 보여 줍니다.")
    st.caption(f"적용 연도: {profile['year']}학년도")

    st.divider()
    st.header("Agent Information")
    st.write("**Role**")
    st.write("에듀루트 업무 길잡이 (EduRoute Task Guide)")
    st.write("**Goal**")
    st.write("교사가 담당 업무의 흐름과 기한을 스스로 파악하고 확정하도록 근거를 들어 안내")
    st.write("**Agent Architecture**")
    st.code(
        "Teacher\n  ↓ 개인정보 마스킹 (프로그램)\nSingle Agent (LLM)\n  ↔ Tools (조회·후보 등록)\n"
        "  ↓\n답변 + 근거 + 확인 대기\n  ↓\nTeacher Choice (확정)",
        language=None,
    )
    use_agent = llm_config.has_api_key()
    if use_agent:
        st.success(f"🤖 싱글 에이전트 작동 중 · {llm_config.model_name()}")
    else:
        st.warning("Gemini 키 없음 → 규칙 기반 임시 응답기로 동작합니다.")
        with st.expander("키를 어디서 찾았나요?"):
            st.text("\n".join(llm_config.diagnose()))
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_session = new_agent_session()  # 에이전트 기억도 새로 시작
        st.rerun()

# 4. 화면 제목 #
st.title("🧭 에듀루트 업무 길잡이")
st.caption("AI가 일정을 대신 정하지 않습니다. 근거를 확인하고 기한을 확정하는 것은 선생님입니다.")

tab_roadmap, tab_chat = st.tabs(["📅 업무 로드맵", "💬 업무 길잡이"])

# 5. 로드맵 탭 (고정 워크플로우 결과) #
with tab_roadmap:
    cards = data_store.get_cards()
    total, done_count = len(cards), len(st.session_state.done & {c["card_id"] for c in cards})
    st.progress(done_count / total, text=f"완료 {done_count} / {total}")

    months = sorted({c["month"] for c in cards})
    current = date.today().month
    view = st.radio(
        "월 선택",
        ["전체"] + [f"{m}월" for m in months],
        index=(months.index(current) + 1) if current in months else 0,
        horizontal=True,
    )
    shown = cards if view == "전체" else data_store.get_cards(int(view[:-1]))

    for card in shown:
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{card['month']}월 · {card['title']}**")
                due_text = f" · 기한 **{card['due']}**" if card["due"] else ""
                st.caption(f"{STATUS_BADGE[card['status']]} · {card['period']}{due_text}")
            with right:
                checked = st.checkbox("완료", value=card["card_id"] in st.session_state.done, key=f"done_{card['card_id']}")
                if checked:
                    st.session_state.done.add(card["card_id"])
                else:
                    st.session_state.done.discard(card["card_id"])
            if card["tip"]:
                st.markdown(f"💡 {card['tip']}")
            for doc_id in card["doc_ids"]:
                doc = data_store.get_document(doc_id)
                with st.expander(f"근거 공문 {doc_id}"):
                    st.markdown(f"**{doc['title']}** ({doc['issued']} 시행)")
                    st.write(doc["summary"])
            if card["due"] and st.button("이 기한을 확인 대기에 올리기", key=f"pend_{card['card_id']}"):
                add_pending(card["title"], card["due"], ", ".join(card["doc_ids"]) or "로드맵")
                st.toast("확인 대기에 추가했습니다.")

# 6. 업무 길잡이 탭 (채팅) #
with tab_chat:
    st.caption("예) \"3월에 뭐부터 해야 해요?\" · \"외부강사 채용 공문 있어요?\" · 받은 업무 메시지 붙여넣기")

    chat_box = st.container(height=480)
    with chat_box:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("masked"):
                    with st.expander("🔒 마스킹된 개인정보"):
                        for item in message["masked"]:
                            st.write(f"{item['type']}: {item['masked']}")
                if message.get("tools"):
                    with st.expander(f"🛠 에이전트가 사용한 도구 ({len(message['tools'])})"):
                        for call in message["tools"]:
                            st.code(call, language=None)

    user_input = st.chat_input("궁금한 업무나 받은 메시지를 입력하세요.")
    if user_input:
        # 에이전트(LLM)에 보내기 전에 프로그램이 마스킹한다.
        masked_input, masked_items = mask_text(user_input)
        st.session_state.messages.append({"role": "user", "content": masked_input, "masked": masked_items})
        with chat_box:
            with st.chat_message("user"):
                st.markdown(masked_input)

        tool_calls = []
        if use_agent:
            agent_profile = {**selected, "year": profile["year"]}
            with chat_box, st.spinner("에이전트가 자료를 찾고 있습니다..."):
                try:
                    reply, proposals, tool_calls = ask_agent(masked_input, agent_profile)
                except Exception as e:
                    reply, proposals = f"⚠️ 에이전트 실행 중 오류가 발생했습니다: {e}", []
        else:
            reply, proposals = mock_reply(masked_input, profile)
        for p in proposals:
            add_pending(p["task"], p["date"], p["source"])
        st.session_state.messages.append({"role": "assistant", "content": reply, "tools": tool_calls})
        st.rerun()

# 7. 확인 대기 기한 (Teacher Choice) #
st.divider()
st.subheader("⏳ 확인 대기 기한")
st.caption("원문과 대조한 뒤 날짜를 고치고 확정하세요. 확정한 기한만 일정에 등록됩니다.")

if not st.session_state.pending:
    st.write("확인 대기 중인 기한이 없습니다.")
for item in list(st.session_state.pending):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        c1.markdown(f"**{item['task']}**  \n근거: {item['source']}")
        new_date = c2.date_input("기한", value=date.fromisoformat(item["date"]), key=f"date_{item['id']}")
        if c3.button("확정", key=f"ok_{item['id']}", type="primary"):
            st.session_state.confirmed.append({**item, "date": new_date.isoformat()})
            st.session_state.pending.remove(item)
            st.rerun()
        if c4.button("삭제", key=f"del_{item['id']}"):
            st.session_state.pending.remove(item)
            st.rerun()

if st.session_state.confirmed:
    st.subheader("✅ 확정한 기한")
    st.caption("데모에서는 목록에만 저장합니다. 실제 서비스에서는 이 목록만 구글 캘린더에 등록하고 마감 3일 전 알림을 설정합니다.")
    st.dataframe(
        [{"업무": c["task"], "기한": c["date"], "근거": c["source"]} for c in st.session_state.confirmed],
        hide_index=True,
        use_container_width=True,
    )
