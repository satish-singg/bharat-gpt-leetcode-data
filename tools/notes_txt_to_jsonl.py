import json, re, sys
n = int(sys.argv[1]); rows = [json.loads(l) for l in open("annotate/batch_%04d.jsonl" % n)]
txt = open(sys.argv[2]).read(); parts = re.split(r"^## (\d+)\s*$", txt, flags=re.M); got = {}
for i in range(1, len(parts), 2): got[int(parts[i])] = "\n".join(l.strip() for l in parts[i + 1].strip().split("\n") if l.strip())
import os; os.makedirs("annotated", exist_ok=True)
with open("annotated/batch_%04d.jsonl" % n, "w") as f:
    for k, r in enumerate(rows, 1):
        if k in got: f.write(json.dumps({"id": r["id"], "notes": got[k]}) + "\n")
print(n, "notes", len(got), "of", len(rows))
