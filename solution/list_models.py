import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
with urllib.request.urlopen(req, timeout=3) as r:
    data = json.loads(r.read())
    print("Available in Ollama:")
    for m in data.get('models', []):
        size_mb = m.get('size', 0) / (1024 * 1024)
        print(f" - {m['name']} ({size_mb:.1f} MB)")
