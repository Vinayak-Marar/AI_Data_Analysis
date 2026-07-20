import re
from agent.llm_factory import get_llm
from agent.prompts import ANALYZER_PROMPT
from agent.state import AnalysisState, Finding
from sandbox.executor import run_python_code
from tools.data_loader import load_dataframe
import config


def _clean_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_steps(plan: str) -> list[str]:
    steps = []
    for line in plan.split("\n"):
        line = line.strip()
        m = re.match(r"^\d+[\.\)]\s*(.+)", line)
        if m:
            steps.append(m.group(1).strip())
    return steps if steps else [plan.strip()]


def _build_full_code(dataset_path: str, llm_code: str) -> str:
    cleaned = []
    for line in llm_code.split("\n"):
        s = line.strip()
        if s.startswith("import pandas") or s.startswith("from pandas"):
            continue
        if "pd.read_csv" in s or "pd.read_excel" in s:
            continue
        if s.startswith("DATA_PATH") and "=" in s:
            continue
        cleaned.append(line)
    llm_clean = "\n".join(cleaned).strip()

    if dataset_path.endswith(".csv"):
        loader = f"import pandas as pd\ndf = pd.read_csv(r'{dataset_path}')\n"
    else:
        loader = f"import pandas as pd\ndf = pd.read_excel(r'{dataset_path}')\n"

    datetime_fix = (
        "import datetime\n"
        "for _col in df.select_dtypes(include=['datetime64']).columns:\n"
        "    df[_col] = df[_col].astype(str)\n"
        "for _col in df.columns:\n"
        "    if len(df) > 0 and isinstance(df[_col].iloc[0], datetime.time):\n"
        "        df[_col] = df[_col].astype(str)\n"
    )
    return loader + datetime_fix + llm_clean


def _safe_correlation_code(dataset_path: str) -> str:
    loader = _build_full_code(dataset_path, "")
    return loader + """
numeric_cols = df.select_dtypes(include='number').columns.tolist()
if len(numeric_cols) >= 2:
    corr_df = df[numeric_cols].corr(numeric_only=True).round(3)
    print("=== Correlation Matrix ===")
    print(corr_df.to_string())
else:
    print("Not enough numeric columns for correlation.")
"""


def _safe_categorical_code(dataset_path: str) -> str:
    loader = _build_full_code(dataset_path, "")
    return loader + """
cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
for col in cat_cols[:8]:
    vc = df[col].value_counts().reset_index()
    vc.columns = [col, 'count']
    vc['percentage'] = (vc['count'] / len(df) * 100).round(1)
    print(f"=== {col} distribution ===")
    print(vc.head(10).to_string(index=False))
    print()
"""


def _safe_missing_code(dataset_path: str) -> str:
    loader = _build_full_code(dataset_path, "")
    return loader + """
missing_df = pd.DataFrame({
    'column': df.columns,
    'missing_count': df.isnull().sum().values,
    'missing_pct': (df.isnull().sum() / len(df) * 100).round(2).values
})
missing_df = missing_df[missing_df['missing_count'] > 0].sort_values('missing_count', ascending=False)
duplicates = df.duplicated().sum()
print("=== Missing Values ===")
if missing_df.empty:
    print("No missing values found.")
else:
    print(missing_df.to_string(index=False))
print(f"\\n=== Duplicate Rows: {duplicates} ===")
"""


def _safe_stats_code(dataset_path: str) -> str:
    loader = _build_full_code(dataset_path, "")
    return loader + """
numeric_cols = df.select_dtypes(include='number').columns.tolist()
if numeric_cols:
    stats_df = df[numeric_cols].describe().round(2)
    print("=== Descriptive Statistics ===")
    print(stats_df.to_string())
else:
    print("No numeric columns found.")
"""


def _detect_safe_pattern(step: str) -> str | None:
    step_lower = step.lower()
    if any(kw in step_lower for kw in ["correlation", "corr_df", "correlation matrix"]):
        return "correlation"
    if any(kw in step_lower for kw in ["categorical", "value_counts", "category_df"]):
        return "categorical"
    if any(kw in step_lower for kw in ["missing", "duplicate", "quality", "null"]):
        return "missing"
    if any(kw in step_lower for kw in ["descriptive statistic", "stats_df", "statistical summary"]):
        return "stats"
    return None


def _extract_dataframe_names(code: str) -> list[str]:
    names = []
    for match in re.finditer(r"^([a-z_][a-z0-9_]*_df)\s*=", code, re.MULTILINE):
        name = match.group(1)
        if name != "df" and name not in names:
            names.append(name)
    return names


def _make_summary(step: str, stdout: str) -> str:
    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    preview = " | ".join(lines[:3]) if lines else "No output"
    return f"{step[:80]} → {preview[:200]}"


def analyze_node(state: AnalysisState) -> AnalysisState:
    llm = get_llm(state["model_key"])
    steps = _extract_steps(state["plan"])
    df = load_dataframe(state["dataset_path"])
    columns = list(df.columns)
    columns_str = "\n".join(f"  - {c}" for c in columns)

    for step in steps:
        safe_pattern = _detect_safe_pattern(step)

        if safe_pattern:
            if safe_pattern == "correlation":
                full_code = _safe_correlation_code(state["dataset_path"])
            elif safe_pattern == "categorical":
                full_code = _safe_categorical_code(state["dataset_path"])
            elif safe_pattern == "missing":
                full_code = _safe_missing_code(state["dataset_path"])
            else:
                full_code = _safe_stats_code(state["dataset_path"])

            print(f"\n=== SAFE CODE: {step[:60]} ===")
            result = run_python_code(full_code, state["working_dir"])
            if result["success"]:
                finding: Finding = {
                    "step": step,
                    "summary": _make_summary(step, result["stdout"]),
                    "stdout": result["stdout"],
                    "analysis_code": full_code,
                    "created_dataframes": _extract_dataframe_names(full_code),
                    "important_columns": [],
                    "status": "success",
                }
                state["findings"].append(finding)
                state["code_history"].append(full_code)
                state["execution_results"].append(result["stdout"])
                continue

        error = None
        succeeded = False
        for attempt in range(4):
            prompt = ANALYZER_PROMPT.format(
                step=step, columns=columns_str, error=error or "None"
            )
            response = llm.invoke(prompt)
            print(f"\n--- LLM (analyzer attempt {attempt+1}) ---")
            print(response.content)

            code = _clean_code(response.content)
            full_code = _build_full_code(state["dataset_path"], code)
            result = run_python_code(full_code, state["working_dir"])

            print("Success:", result["success"])
            print("Stderr:", result["stderr"][:300])

            if result["success"]:
                finding: Finding = {
                    "step": step,
                    "summary": _make_summary(step, result["stdout"]),
                    "stdout": result["stdout"],
                    "analysis_code": full_code,
                    "created_dataframes": _extract_dataframe_names(code),
                    "important_columns": [c for c in columns if c in code],
                    "status": "success",
                }
                state["findings"].append(finding)
                state["code_history"].append(full_code)
                state["execution_results"].append(result["stdout"])
                succeeded = True
                break
            else:
                error = result["stderr"][-600:]

        if not succeeded and not safe_pattern:
            finding: Finding = {
                "step": step,
                "summary": f"FAILED: {step[:80]}",
                "stdout": "",
                "analysis_code": "",
                "created_dataframes": [],
                "important_columns": [],
                "status": "failed",
            }
            state["findings"].append(finding)

    return state