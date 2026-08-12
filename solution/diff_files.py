with open('solution/answers_submission.csv', 'r') as f1, open('solution/answers_qwen35.csv', 'r') as f2:
    lines1 = f1.readlines()
    lines2 = f2.readlines()

diffs = []
for i, (l1, l2) in enumerate(zip(lines1, lines2)):
    if l1 != l2:
        diffs.append((i+1, l1.strip(), l2.strip()))

print(f"Total line count: {len(lines1)} vs {len(lines2)}")
print(f"Line differences count: {len(diffs)}")
for d in diffs[:5]:
    print(f"  Line {d[0]}: f1='{d[1]}' vs f2='{d[2]}'")
