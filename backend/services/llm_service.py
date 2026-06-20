import requests
from backend.config import get_settings


def llm_health():
    settings = get_settings()
    try:
        base = settings.ollama_base_url.rstrip("/")
        url = base.replace("/v1", "") + "/api/tags"
        response = requests.get(url, timeout=2)
        return {"reachable": response.ok, "status_code": response.status_code if response is not None else None, "model": settings.ollama_model}
    except Exception as exc:
        return {"reachable": False, "error": "Ollama is not reachable.", "model": settings.ollama_model}
