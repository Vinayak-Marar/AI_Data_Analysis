from typing import TypedDict, List, Optional


class Finding(TypedDict):
    step: str
    summary: str
    stdout: str
    analysis_code: str
    created_dataframes: List[str]
    important_columns: List[str]
    status: str


class AnalysisState(TypedDict):
    dataset_path: str
    working_dir: str
    user_question: str
    data_profile: str
    model_key: str          # ← new
    plan: Optional[str]
    code_history: List[str]
    execution_results: List[str]
    findings: List[Finding]
    chart_paths: List[str]
    report_path: Optional[str]
    error: Optional[str]