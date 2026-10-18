"""Gemini 키가 제대로 연결됐는지 확인하는 스크립트. 어느 폴더에서 실행해도 된다.

실행: python check_gemini.py
"""
from agents import Agent, Runner

import llm_config

print("[키 확인]")
print("\n".join(llm_config.diagnose()))
if not llm_config.has_api_key():
    raise SystemExit("\nGEMINI_API_KEY가 없어 연결 확인을 중단합니다.")

agent = Agent(name="연결 확인", instructions="한국어로 한 문장만 답한다.", model=llm_config.build_model())
result = Runner.run_sync(agent, "연결 확인용 인사를 해 줘.")
print(f"\n[{llm_config.model_name()}] {result.final_output}")
print("Gemini 연결 성공")
