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
for f in sorted(glob.glob("fixnotes/out/batch_*.jsonl")):
    b = re.search(r"batch_(\d+)", f).group(1); sol = f"data/solutions/batch_{b}.jsonl"
    if not os.path.exists(sol): print("no", sol); continue
    recs = [json.loads(l) for l in open(sol, encoding="utf-8") if l.strip()]
    byid = {f"{r['number']}:{r['language']}:{r['approach_id']}": r for r in recs}
    changed = 0
    for l in open(f, encoding="utf-8"):
        if not l.strip(): continue
        o = json.loads(l); r = byid.get(o["id"])
        if r is None: print("REJECT", b, o.get("id"), "| id not in", sol); rej += 1; continue
        probs = V.check({"notes": o.get("notes", "")}, r["code"])
        cr = o.get("complexity_reason") or ""
        if len(cr.split()) < 8 or TEMPLATE_REASON.search(cr): probs.append("complexity_reason missing, too short or the old template sentence")
        if probs: print("REJECT", b, o["id"], "|", "; ".join(probs)[:200]); rej += 1; continue
        r["notes"] = o["notes"]; r["complexity_reason"] = cr; changed += 1; ok += 1
    rep = f"tests/batch_{b}-test-report.md"
    for r in recs:
        if r["language"] == "java21": r["language"] = "java"
        if os.path.exists(rep) and r.get("status") == "pending":
            t = open(rep, encoding="utf-8").read()
            if "PASS" in t and "FAIL" not in t and r.get("self_check", {}).get("ran") and r["self_check"].get("examples_passed") == r["self_check"].get("examples_total"): r["status"] = "verified"
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
