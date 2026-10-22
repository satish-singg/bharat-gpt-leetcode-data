#!/usr/bin/env python3
"""Cut the mined solutions that have no written note (kamyu/Anas, Python 3, tier A/B = passed the statement examples) into annotation batches for a teacher (ChatGPT or a rented-GPU model).
The teacher returns one JSON line per input: {"id": <same id>, "notes": "<six labelled lines>"} ; `notes` then becomes the <think> text of that record (tools/merge_annotations.py).
  python3 tools/make_annotation_batches.py --repo <data repo> --out <data repo>/annotate --size 20 --limit 0"""
import argparse, gzip, json, os
ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--out", required=True); ap.add_argument("--size", type=int, default=20); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
U = os.path.join(a.repo, "corpus", "unified")
probs = {}
for l in gzip.open(os.path.join(U, "problems.jsonl.gz"), "rt"):
    p = json.loads(l)
    if p["origin"] in ("anas_kamyu", "doocs_huajianmao"): probs.setdefault(p["number"], p)
rows = []
for l in gzip.open(os.path.join(U, "solutions.jsonl.gz"), "rt"):
    s = json.loads(l)
    if s["source"] in ("kamyu104", "anas") and s["language"] == "python3" and s["tier"] in ("A", "B") and not s.get("think") and s["number"] in probs:
        rows.append({"id": "%d:%s:%s" % (s["number"], s["source"], s["approach_name"]), "number": s["number"], "title": s["title"], "statement": probs[s["number"]]["statement"], "code": s["code"],
                     "time_complexity": s["time_complexity"], "space_complexity": s["space_complexity"], "complexity_source": s.get("complexity_evidence")})
rows.sort(key=lambda r: (r["number"], r["id"]))
if a.limit: rows = rows[:a.limit]
os.makedirs(a.out, exist_ok=True)
for i in range(0, len(rows), a.size):
    with open(os.path.join(a.out, "batch_%04d.jsonl" % (i // a.size + 1)), "w") as f:
        for r in rows[i:i + a.size]: f.write(json.dumps(r) + "\n")
print(len(rows), "records ->", (len(rows) + a.size - 1) // a.size, "batches in", a.out)
