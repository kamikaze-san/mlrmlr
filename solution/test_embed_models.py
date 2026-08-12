import urllib.request
import json
import numpy as np

def test_embed_model(model_name):
    print(f"Testing embedding model: {model_name}")
    data = {'model': model_name, 'prompt': 'What is the exact surplus value separating highest from next down?'}
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/embeddings',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            vec = res.get('embedding', [])
            print(f"  Success! Vector dimension: {len(vec)}")
            return len(vec)
    except Exception as e:
        print(f"  Error: {e}")
        return None

test_embed_model('nomic-embed-text:latest')
test_embed_model('hf.co/CompendiumLabs/bge-base-en-v1.5-gguf:latest')
