#!/usr/bin/env python3
"""Compare ChatGPT's verdicts (verify/results/X.results.jsonl) with the runner (verify/runner/X.runner.jsonl). Prints a table and lists disagreements (runner says quarantined but ChatGPT said pass, or the reverse).
  python3 tools/compare_verify.py pending_3_of_6"""
import json, sys, collections, os
name = sys.argv[1]
gpt = {}
p = f"verify/results/{name}.results.jsonl"
if os.path.exists(p):
    for l in open(p):
        if l.strip(): r = json.loads(l); gpt[r["id"]] = r.get("verdict", "?")
run = {json.loads(l)["id"]: json.loads(l) for l in open(f"verify/runner/{name}.runner.jsonl") if l.strip()}
tab = collections.Counter(); bad = []
for i, r in run.items():
    g = gpt.get(i, "no_chatgpt_result"); tab[(r["status"], g)] += 1
    if (r["status"] == "quarantined" and g == "pass") or (r["status"] == "public_tests_passed" and g == "fail"): bad.append((i, g, r["status"], r["reason"][:100]))
print(f"## {name}\n\n| runner | chatgpt | records |\n|---|---|---|")
for (a, b), n in sorted(tab.items()): print(f"| {a} | {b} | {n} |")
print(f"\nDisagreements: {len(bad)}")
for b in bad: print("- " + " | ".join(map(str, b)))
