import json, re

entries = [json.loads(l) for l in open(
    r'C:\Users\NewGr\Downloads\hackathon_rlm\logs\rlm_2026-08-10_08-42-43_87020b85.jsonl',
    encoding='utf-8')]
iters = [e for e in entries if e.get('type') == 'iteration']
blocks = []
start = 0
for i in range(1, len(iters)):
    if iters[i]['iteration'] == 1:
        blocks.append(iters[start:i])
        start = i
blocks.append(iters[start:])

qids = ["HS-IC-0002", "HS-IC-0004", "HS-IC-0006", "HS-IC-0010", "HS-IC-0011",
        "HS-IC-0012", "HS-IC-0016", "HS-IC-0018", "HS-IC-0019", "HS-IC-0020",
        "HS-IC-0021", "HS-IC-0023", "HS-IC-0024", "HS-IC-0025"]

cache_call_re = re.compile(r'cache_lookup\(["\']([^"\']+)["\']\)')
ctx_probe_re = re.compile(r'context_\d+|history_\d+')

out = []
for qid, block in zip(qids, blocks):
    n_iters = len(block)
    cache_calls = []
    probe_iters = 0
    for e in block:
        r = e['response']
        cache_calls.extend(cache_call_re.findall(r))
        if len(ctx_probe_re.findall(r)) >= 2:  # multiple context_N/history_N mentions = probing
            probe_iters += 1
    out.append(f"{qid}: {n_iters} iters | cache_lookup calls: {cache_calls} | probing iters: {probe_iters}")

print("\n".join(out))
