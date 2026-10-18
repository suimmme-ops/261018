# 에듀루트 업무 길잡이 — 싱글 에이전트 데모

에듀루트(공문 → 월별 업무 로드맵)에 싱글 에이전트 "업무 길잡이"를 붙인 데모입니다.

- **Gemini 키가 있으면**: 채팅 답변을 싱글 에이전트(Gemini + Instructions + SQLiteSession 멀티턴 + 도구 4종)가 만듭니다.
- **키가 없으면**: 규칙 기반 임시 응답기(`responder.py`)로 동작합니다.

| 구성 | 파일 |
|---|---|
| Agent 정의, 동적 Instructions (ROLE·GOAL·CONTEXT·RULES·PROCESS·OUTPUT) | `agent_setup.py` |
| Tools: `search_documents`, `get_roadmap`, `check_date`, `propose_deadline` | `tools.py` |
| Runner 실행, SQLiteSession 멀티턴 | `app.py`의 `ask_agent()` |
| Gemini 모델 연결 | `llm_config.py` |

채팅 답변 아래 **🛠 에이전트가 사용한 도구**를 펼치면 에이전트가 어떤 도구를 골랐는지 볼 수 있습니다.

## 실행 (GitHub Codespaces)

저장소 최상위에 `eduroute_agent/` 폴더와 `.devcontainer/` 폴더를 함께 올립니다.

- **새 코드스페이스를 만들거나 Rebuild Container를 하면**: 패키지 설치와 `streamlit run`이 자동으로 실행되고, 8501 포트 미리보기가 열립니다.
- **이미 열린 코드스페이스에서 바로 실행하려면**:

```bash
cd eduroute_agent
pip install -r requirements.txt
streamlit run app.py
```

Phase A는 API 키가 없어도 실행됩니다.

## Gemini API 키 전달

코드에 키를 적지 않습니다. 아래 둘 중 하나를 씁니다. 읽는 순서는 `llm_config.py`에 있습니다 (환경변수 → secrets.toml).

1. **Codespaces Secrets (권장)**: GitHub [Settings] → [Codespaces] → [New secret]
   - Name: `GEMINI_API_KEY` / Value: Google AI Studio에서 발급한 키 / 저장소 선택
   - 이미 열려 있는 코드스페이스는 **재시작해야** 키가 들어옵니다.
2. **secrets.toml (로컬 PC용)**: `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사한 뒤 키를 넣습니다 (`.gitignore`로 커밋에서 제외됨).

연결 확인:

```bash
cd eduroute_agent
python check_gemini.py
```

사이드바에 "Gemini 키 연결됨"이 보이면 키를 읽은 것입니다. 모델은 기본값 `gemini-2.5-flash`이며, `GEMINI_MODEL`로 바꿀 수 있습니다.

> 원리: OpenAI Agents SDK는 기본적으로 OpenAI 모델을 쓰지만, Gemini의 OpenAI 호환 주소(`https://generativelanguage.googleapis.com/v1beta/openai/`)를 `AsyncOpenAI` 클라이언트에 넣고 `OpenAIChatCompletionsModel`로 감싸면 `Agent(model=...)`에 그대로 쓸 수 있습니다. 트레이싱은 OpenAI 키가 필요해서 꺼 둡니다.

## 샘플 업무

중학교 · 서울 · 샘플교육지원청 · **방과후학교 업무** (2026학년도)
공문 9건(`data/documents.json`)과 로드맵 카드 13개(`data/roadmap.json`)는 모두 **가상 데이터**입니다.

## 파일 구성

| 파일 | 역할 | Phase B·C에서 |
|---|---|---|
| `app.py` | Streamlit 화면 (사이드바, 로드맵 탭, 채팅 탭, 확인 대기 패널) | `mock_reply` 호출을 `Runner.run_sync`로 교체 |
| `responder.py` | 임시 응답기 (월별 할 일 / 공문 검색 / 메시지 기한 추출·되묻기) | Agent 정의로 대체 |
| `data_store.py` | 공문·로드맵 조회 | `search_documents`, `get_roadmap` Tool이 감쌈 |
| `dates.py` | 날짜 찾기·검증, D-day | `check_date` Tool이 감쌈 |
| `masking.py` | 개인정보 마스킹 (에이전트 호출 전 항상 실행) | 그대로 사용 |
| `llm_config.py` | Gemini 키 읽기, Agent용 모델 생성 | `Agent(model=build_model())` |
| `check_gemini.py` | 키 연결 확인 스크립트 | — |

## 데모 시나리오

1. `3월에 뭐부터 해야 해요?` → `get_roadmap(3)` → 3월 업무 + 근거 공문 + 경험 팁
2. `방과후 강사 만족도 결과 다음 주 중으로 제출 바랍니다. 담당 김철수 010-1234-5678` → 마스킹 + 기한이 모호하다며 되묻기
3. (이어서) `10월 23일이요` → 멀티턴으로 앞의 업무를 이어받아 `check_date` → `propose_deadline` → 확인 대기 → [확정]
4. `작년 학교평가 일정 알려줘` → `search_documents` 결과 없음 → "확인 필요" 안내 (날짜를 지어내지 않음)
