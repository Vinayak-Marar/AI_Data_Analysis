from agent.llm_factory import get_llm
from agent.prompts import PLANNER_PROMPT
from agent.state import AnalysisState


def plan_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm(state["model_key"])
    prompt = PLANNER_PROMPT.format(
        profile=state["data_profile"],
        question=state["user_question"],
    )
    response = llm.invoke(prompt)
    state["plan"] = response.content.strip()
    print("\n=== PLAN ===")
    print(state["plan"])
    print("=== END PLAN ===\n")
    return state