#!/usr/bin/env python3
"""Applies the fixed notes: reads fixnotes/out/batch_NNNN.jsonl ({"id","notes","complexity_reason"}), checks every record with tools/validate_notes.py and writes the accepted ones into
data/solutions/batch_NNNN.jsonl (fields `notes`, `complexity_reason`; language label java21 -> java). Also: status becomes "verified" for batches whose tests/batch_NNNN-test-report.md exists,
shows only PASS and no FAIL. Rejected lines are listed - fix them in fixnotes/out and run again. Annotation redo: fixnotes/redo_annotations_out.jsonl is copied to annotated/redo.jsonl when valid
(lines with "flag" instead of notes are collected in fixnotes/flagged_code.jsonl).
  python3 tools/apply_notes_fix.py"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_notes as V

TEMPLATE_REASON = re.compile(r"bounded number of times|algorithm's stack, DP, or collection state|each input element or state", re.I)
ok = rej = 0
# Fix batches are numbered separately from solution batches, so ids are looked up across ALL solution files.
files = {}; index = {}
for sol in sorted(glob.glob("data/solutions/batch_*.jsonl")):
    recs = [json.loads(l) for l in open(sol, encoding="utf-8") if l.strip()]
    files[sol] = recs
    for r in recs: index[f"{r['number']}:{r['language'].replace('java', 'java21') if r['language'] == 'java' else r['language']}:{r['approach_id']}"] = (sol, r)
    for r in recs:   # ids may also be keyed with the label already normalised to java
        index.setdefault(f"{r['number']}:{r['language']}:{r['approach_id']}", (sol, r))
changed_files = set()
for f in sorted(glob.glob("fixnotes/out/batch_*.jsonl")):
    for l in open(f, encoding="utf-8"):
        if not l.strip(): continue
        o = json.loads(l); hit = index.get(o["id"])
        if hit is None: print("REJECT", f, o.get("id"), "| id not found in any data/solutions file"); rej += 1; continue
        sol, r = hit
        probs = V.check({"notes": o.get("notes", "")}, r["code"])
        cr = o.get("complexity_reason") or ""
        if len(cr.split()) < 8 or TEMPLATE_REASON.search(cr): probs.append("complexity_reason missing, too short or the old template sentence")
        if probs: print("REJECT", f, o["id"], "|", "; ".join(probs)[:200]); rej += 1; continue
        r["notes"] = o["notes"]; r["complexity_reason"] = cr; changed_files.add(sol); ok += 1
for sol, recs in files.items():
    b = re.search(r"batch_(\d+)", sol).group(1); rep = f"tests/batch_{b}-test-report.md"; changed = sol in changed_files
    for r in recs:
        if r["language"] == "java21": r["language"] = "java"; changed = True
        if os.path.exists(rep) and r.get("status") == "pending":
            t = open(rep, encoding="utf-8").read()
            if "PASS" in t and "FAIL" not in t and r.get("self_check", {}).get("ran") and r["self_check"].get("examples_passed") == r["self_check"].get("examples_total"): r["status"] = "verified"; changed = True
    if changed:
        with open(sol, "w", encoding="utf-8") as g:
            for r in recs: g.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"solution notes applied {ok}, rejected {rej}")

src = "fixnotes/redo_annotations_out.jsonl"
if os.path.exists(src):
    code = {}
    for f in glob.glob("annotate/*.jsonl"):
        for l in open(f, encoding="utf-8"):
            if l.strip(): r = json.loads(l); code[r["id"]] = r["code"]
    good, flagged, bad = [], [], 0
    for l in open(src, encoding="utf-8"):
        if not l.strip(): continue
        o = json.loads(l)
        if o.get("flag"): flagged.append(o); continue
        p = V.check(o, code.get(o["id"], ""))
        if p: print("REJECT redo", o["id"], "|", "; ".join(p)[:200]); bad += 1
        else: good.append({"id": o["id"], "notes": o["notes"]})
    with open("annotated/redo.jsonl", "w", encoding="utf-8") as g:
        for r in good: g.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("fixnotes/flagged_code.jsonl", "w", encoding="utf-8") as g:
        for r in flagged: g.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"annotation redo: accepted {len(good)}, flagged as wrong code {len(flagged)}, rejected {bad}")
