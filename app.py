from flask import Flask, request, render_template, send_file
import os
import uuid

import config
from tools.data_loader import load_dataframe
from tools.profiler import profile_dataframe
from agent.graph import build_graph

app = Flask(__name__)
agent_graph = build_graph()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", models=config.AVAILABLE_MODELS)


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files["dataset"]
    question = request.form["question"]
    model_key = request.form.get("model_key", "groq_llama70b")

    # Validate
    if model_key not in config.AVAILABLE_MODELS:
        model_key = "groq_llama70b"

    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    df = load_dataframe(filepath)
    profile = profile_dataframe(df)

    print(f"\n=== USING MODEL: {config.AVAILABLE_MODELS[model_key]['label']} ===\n")

    initial_state = {
        "dataset_path": os.path.abspath(filepath),
        "working_dir": os.path.abspath(config.UPLOAD_FOLDER),
        "user_question": question,
        "data_profile": profile,
        "model_key": model_key,
        "plan": None,
        "code_history": [],
        "execution_results": [],
        "findings": [],
        "chart_paths": [],
        "report_path": None,
        "error": None,
    }

    final_state = agent_graph.invoke(initial_state)

    return render_template(
        "results.html",
        plan=final_state["plan"],
        findings=final_state["findings"],
        charts=final_state["chart_paths"],
        report_path=final_state["report_path"],
        model_used=config.AVAILABLE_MODELS[model_key]["label"],
    )


@app.route("/download/report")
def download_report():
    report_path = os.path.join(config.REPORTS_FOLDER, "report.docx")
    return send_file(report_path, as_attachment=True, download_name="analysis_report.docx")


if __name__ == "__main__":
    app.run(debug=True, port=5000)