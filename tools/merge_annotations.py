#!/usr/bin/env python3
"""Merge teacher notes ({"id","notes"} lines in <repo>/annotated/*.jsonl) into corpus/unified: sets `notes` and `think` for matching records and re-renders nothing - run tools/unify_corpus.py afterwards
(unify reads corpus/annotations.jsonl.gz and uses it). Rejects notes that are not exactly the six labelled lines or are outside 60-300 words."""
import argparse, glob, gzip, json, os, re
ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); a = ap.parse_args()
LAB = ["Task and constraints:", "Idea:", "Technique and why it applies:", "Invariant:", "Edge cases:", "Complexity:"]
ok = bad = 0; out = {}
for f in sorted(glob.glob(os.path.join(a.repo, "annotated", "*.jsonl"))):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l); lines = r.get("notes", "").split("\n"); w = len(r.get("notes", "").split())
        if len(lines) == 6 and all(x.startswith(y) for x, y in zip(lines, LAB)) and 60 <= w <= 300 and not re.search(r"\b(wait|hmm|let's think)\b", r["notes"], re.I): out[r["id"]] = r["notes"]; ok += 1
        else: bad += 1
with gzip.open(os.path.join(a.repo, "corpus", "annotations.jsonl.gz"), "wt") as g:
    for k, v in out.items(): g.write(json.dumps({"id": k, "notes": v}) + "\n")
print("accepted", ok, "rejected", bad)
