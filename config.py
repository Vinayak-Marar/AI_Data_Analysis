import os
from dotenv import load_dotenv

load_dotenv()

# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"

# Groq
GROQ_API_KEY = os.environ.get("SECRET_KEY")

# Available models
AVAILABLE_MODELS = {
    "groq_llama70b": {
        "label": "Groq — Llama 3.3 70B (Online, Fast)",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    },
    "groq_mixtral": {
        "label": "Groq — Mixtral 8x7B (Online, Fast)",
        "provider": "groq",
        "model": "mixtral-8x7b-32768",
    },
    "ollama_qwen_coder": {
        "label": "Ollama — Qwen2.5-Coder 7B (Offline)",
        "provider": "ollama",
        "model": "qwen2.5-coder:7b",
    },
    "ollama_llama31": {
        "label": "Ollama — Llama 3.1 8B (Offline)",
        "provider": "ollama",
        "model": "llama3.1:8b",
    },
}

UPLOAD_FOLDER = "data/uploads"
CHARTS_FOLDER = "static/charts"
REPORTS_FOLDER = "outputs/reports"

for folder in [UPLOAD_FOLDER, CHARTS_FOLDER, REPORTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)