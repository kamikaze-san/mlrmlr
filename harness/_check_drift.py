import json
entries = [json.loads(l) for l in open(
    r'C:\Users\NewGr\Downloads\hackathon_rlm\logs\rlm_2026-08-10_07-34-35_aeae0e11.jsonl',
    encoding='utf-8')]
iters = [e for e in entries if e.get('type') == 'iteration']
fence_repl = "`" * 3 + "repl"
fence_python = "`" * 3 + "python"
fence_bare = "`" * 3

unrecognized = 0
for idx, e in enumerate(iters):
    r = e['response']
    has_code_attempt = ('repl' in r.lower() or fence_bare in r)
    executed = len(e.get('code_blocks', [])) > 0
    if has_code_attempt and not executed:
        unrecognized += 1
        print(f"iter-index {idx} (label iter={e['iteration']}): NO code executed, response snippet:")
        print(repr(r[:200]))
        print()

print("total iterations:", len(iters))
print("iterations with an apparent code attempt but ZERO executed blocks:", unrecognized)
