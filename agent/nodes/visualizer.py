import re
import os
import uuid
from langchain_core.language_models import BaseChatModel
from agent.llm_factory import get_llm
from agent.prompts import VISUALIZER_DECISION_PROMPT, VISUALIZER_PROMPT
from agent.state import AnalysisState
from sandbox.executor import run_python_code
from tools.data_loader import load_dataframe
import config


def _clean_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _build_loader(dataset_path: str) -> str:
    if dataset_path.endswith(".csv"):
        loader = f"import pandas as pd\ndf = pd.read_csv(r'{dataset_path}')\n"
    else:
        loader = f"import pandas as pd\ndf = pd.read_excel(r'{dataset_path}')\n"

    loader += (
        "import datetime\n"
        "for _col in df.select_dtypes(include=['datetime64']).columns:\n"
        "    df[_col] = df[_col].astype(str)\n"
        "for _col in df.columns:\n"
        "    if len(df) > 0 and isinstance(df[_col].iloc[0], datetime.time):\n"
        "        df[_col] = df[_col].astype(str)\n"
    )
    return loader


def _strip_loader_lines(code: str) -> str:
    cleaned = []
    for line in code.split("\n"):
        s = line.strip()
        if s.startswith("import pandas") or s.startswith("from pandas"):
            continue
        if "pd.read_csv" in s or "pd.read_excel" in s:
            continue
        if s.startswith("DATA_PATH") and "=" in s:
            continue
        if s.startswith("import datetime"):
            continue
        if "_col in df.select_dtypes" in s or "_col in df.columns" in s:
            continue
        if "isinstance(df[_col]" in s or "df[_col].astype(str)" in s:
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _decide_chart(finding: dict, llm: BaseChatModel) -> str:
    """Ask LLM to decide chart type. llm passed in from visualize_node."""
    prompt = VISUALIZER_DECISION_PROMPT.format(
        finding_summary=finding["summary"],
        stdout=finding["stdout"][:800],
    )
    response = llm.invoke(prompt)
    decision = response.content.strip().split("\n")[0].strip().upper()
    valid = {
        "NO_CHART", "BAR", "HORIZONTAL_BAR", "LINE", "SCATTER",
        "HISTOGRAM", "BOX", "HEATMAP", "PIE", "STACKED_BAR",
        "GROUPED_BAR", "VIOLIN", "AREA", "TREEMAP",
    }
    return decision if decision in valid else "NO_CHART"


def _get_primary_dataframe(finding: dict) -> str:
    if finding["created_dataframes"]:
        return finding["created_dataframes"][0]
    return "df"


def visualize_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm(state["model_key"])  # ← single llm instance for whole node

    df = load_dataframe(state["dataset_path"])
    columns = list(df.columns)
    columns_str = "\n".join(f"  - {c}" for c in columns)

    for finding in state["findings"]:
        if finding["status"] == "failed":
            finding["chart_path"] = None
            continue

        # Pass llm into _decide_chart
        chart_type = _decide_chart(finding, llm)
        print(f"\n=== CHART DECISION: {chart_type} for: {finding['step'][:60]} ===\n")

        if chart_type == "NO_CHART":
            finding["chart_path"] = None
            continue

        chart_filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        chart_path = os.path.abspath(os.path.join(config.CHARTS_FOLDER, chart_filename))
        dataframe_name = _get_primary_dataframe(finding)

        prompt = VISUALIZER_PROMPT.format(
            step=finding["step"],
            result=finding["stdout"][:600],
            chart_type=chart_type,
            dataframe_name=dataframe_name,
            columns=columns_str,
            chart_path=chart_path,
        )
        response = llm.invoke(prompt)

        print("\n--- LLM RAW OUTPUT (visualizer) ---")
        print(response.content)
        print("--- END ---\n")

        plot_code = _clean_code(response.content)
        plot_code = _strip_loader_lines(plot_code)

        analysis_code_clean = _strip_loader_lines(finding["analysis_code"])

        full_code = (
            _build_loader(state["dataset_path"])
            + "\nimport plotly.express as px\n"
            + "import plotly.graph_objects as go\n\n"
            + analysis_code_clean
            + "\n\n"
            + plot_code
        )

        print("\n--- FINAL FULL CODE (visualizer) ---")
        print(full_code)
        print("--- END ---\n")

        success = False
        for attempt in range(2):
            result = run_python_code(full_code, state["working_dir"])
            print(f"--- EXEC RESULT (visualizer attempt {attempt+1}) ---")
            print("Success:", result["success"])
            print("Stderr:", result["stderr"][:400])
            print("--- END ---\n")

            if result["success"] and os.path.exists(chart_path):
                state["chart_paths"].append(chart_filename)
                finding["chart_path"] = chart_filename
                success = True
                break

        if not success:
            finding["chart_path"] = None

    return state