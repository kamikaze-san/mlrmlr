import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")

class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False, temperature: float = 0.0) -> Optional[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
            }
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res = json.loads(response.read().decode("utf-8"))
                return res.get("response", "").strip()
        except Exception as e:
            print(f"[OllamaClient Error] {e}")
            return None

    def chat(self, messages: List[Dict[str, str]], json_mode: bool = False, temperature: float = 0.0) -> Optional[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
            }
        }
        if json_mode:
            payload["format"] = "json"

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res = json.loads(response.read().decode("utf-8"))
                msg = res.get("message", {})
                return msg.get("content", "").strip()
        except Exception as e:
            print(f"[OllamaClient Error] {e}")
            return None
