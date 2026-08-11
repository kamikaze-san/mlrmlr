import json
entries = [json.loads(l) for l in open(
    r'C:\Users\NewGr\Downloads\hackathon_rlm\logs\rlm_2026-08-10_12-32-37_176589bd.jsonl',
    encoding='utf-8')]
iters = [e for e in entries if e.get('type') == 'iteration']
blocks = []
start = 0
for i in range(1, len(iters)):
    if iters[i]['iteration'] == 1:
        blocks.append(iters[start:i])
        start = i
blocks.append(iters[start:])
block = blocks[0]  # HARD-01
for e in block:
    print('='*10, 'iter', e['iteration'], '='*10)
    for cb in e.get('code_blocks', []):
        res = cb.get('result') or {}
        stdout = res.get('stdout', '')
        print('STDOUT:', repr(stdout[:600]).encode('ascii', 'replace').decode())
