#!/usr/bin/env python3
"""Builds the inputs for the notes-fix task: fixnotes/in/batch_NNNN.jsonl (one line per solution record of data/solutions/batch_NNNN.jsonl, batches 0004-0059 and later ones that fail the checker)
and fixnotes/redo_annotations_in.jsonl (annotation records whose first notes were rejected or flagged). Run from the repo root."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import validate_notes as V

os.makedirs("fixnotes/in", exist_ok=True); os.makedirs("fixnotes/out", exist_ok=True)
prob = {}
for f in glob.glob("data/problems/*.jsonl"):
    for l in open(f, encoding="utf-8"):
        if l.strip(): r = json.loads(l); prob[r["number"]] = r
n_rec = n_files = 0
for f in sorted(glob.glob("data/solutions/batch_*.jsonl")):
    b = re.search(r"batch_(\d+)", f).group(1)
    recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    todo = [r for r in recs if V.check(r)]
    if not todo: continue
    out = os.path.join("fixnotes/in", f"batch_{b}.jsonl")
    with open(out, "w", encoding="utf-8") as g:
        for r in recs:
            if r not in todo: continue
            p = prob.get(r["number"], {})
            g.write(json.dumps({"id": f"{r['number']}:{r['language']}:{r['approach_id']}", "number": r["number"], "title": r["title"], "language": r["language"],
                                "difficulty": p.get("difficulty"), "tags": p.get("tags"), "statement": p.get("statement"), "approach_id": r["approach_id"],
                                "approach_name": r["approach_name"], "code": r["code"], "time_complexity": r["time_complexity"], "space_complexity": r["space_complexity"]}, ensure_ascii=False) + "\n")
    n_rec += len(todo); n_files += 1
print("fixnotes/in:", n_files, "files,", n_rec, "records")

# annotation records to redo: rejected by the checker, or whose note says the code is wrong
code = {}
for f in glob.glob("annotate/*.jsonl"):
    for l in open(f, encoding="utf-8"):
        if l.strip(): r = json.loads(l); code[r["id"]] = r
WRONG = re.compile(r"(is incorrect|incorrectly|not correct|does not correctly|does not implement|implementation is wrong|would be wrong|returns? (a )?wrong|fails? (for|on) |produces? (a )?wrong|collide)", re.I)
redo = []
for f in sorted(glob.glob("annotated/*.jsonl")):
    if os.path.basename(f).startswith("redo"): continue
    for l in open(f, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            if r["id"] in code and (V.check(r, code[r["id"]]["code"]) or WRONG.search(r["notes"])): redo.append(r["id"])
with open("fixnotes/redo_annotations_in.jsonl", "w", encoding="utf-8") as g:
    for i in redo: g.write(json.dumps(code[i], ensure_ascii=False) + "\n")
print("fixnotes/redo_annotations_in.jsonl:", len(redo), "records")
