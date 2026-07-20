from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
import config


def get_llm(model_key: str):
    """Return the correct LLM instance based on model_key from config."""
    model_config = config.AVAILABLE_MODELS.get(model_key)
    if not model_config:
        raise ValueError(f"Unknown model key: {model_key}. Choose from: {list(config.AVAILABLE_MODELS.keys())}")

    provider = model_config["provider"]
    model_name = model_config["model"]

    if provider == "groq":
        return ChatGroq(
            model=model_name,
            api_key=config.GROQ_API_KEY,
            temperature=0,
        )
    elif provider == "ollama":
        return ChatOllama(
            model=model_name,
            base_url=config.OLLAMA_BASE_URL,
            temperature=0,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")