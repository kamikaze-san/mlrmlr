import urllib.request
import json

data = json.dumps({
    "model": "qwen3:4b-instruct",
    "prompt": "Respond with only JSON: {\"status\": \"ok\"}",
    "stream": False,
    "format": "json"
}).encode('utf-8')

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=60) as response:
        res = json.loads(response.read().decode('utf-8'))
        print("Ollama response:", res.get("response"))
except Exception as e:
    print("Error:", e)
