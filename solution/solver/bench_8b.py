import time
import urllib.request
import json

t0 = time.time()
print("Sending test request to qwen3:8b...")
data = json.dumps({
    "model": "qwen3:8b",
    "prompt": "SELECT SUM(value_inr) FROM projects WHERE client_name = 'Test';",
    "stream": False
}).encode('utf-8')

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=120) as response:
        res = json.loads(response.read().decode('utf-8'))
        print(f"Done in {time.time()-t0:.2f}s!")
        print("Response:", res.get("response")[:100])
except Exception as e:
    print(f"Failed in {time.time()-t0:.2f}s with error: {e}")
