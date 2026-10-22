#!/usr/bin/env python3
"""Combine the locked executable-eval task files into ONE file plus a versioned manifest (counts and SHA-256 per input).

  python3 tools/build_locked_manifest.py --out locked_eval_1365.jsonl --manifest locked_eval_1365.manifest.json --expect 1365 \
      doctest=<doctest_unseen.jsonl> leetcode=<lc_unseen.jsonl> codecontests=<cc_unseen.jsonl> taco=<taco_unseen.jsonl>

Each input is NAME=PATH (task rows with "id", "prompt", "reference"). Fails on duplicate ids or when the total differs from --expect.
The combined file is what `--locked` takes in hf_sft_adapter.py, gold_set_check.py, filter-candidates and make_candidate_prompts' companions.
"""
import argparse, hashlib, json, sys


def build(named_paths):
    rows, parts, seen = [], {}, set()
    for name, path in named_paths:
        raw = open(path, "rb").read()
        n = 0
        for line in raw.decode("utf-8").splitlines():
            if not line.strip(): continue
            r = json.loads(line)
            if r["id"] in seen: raise SystemExit(f"duplicate task id {r['id']} (in {name})")
            seen.add(r["id"]); rows.append(r); n += 1
        parts[name] = {"path": path, "tasks": n, "sha256": hashlib.sha256(raw).hexdigest()}
    return rows, parts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--manifest", required=True); ap.add_argument("--expect", type=int)
    ap.add_argument("inputs", nargs="+", help="NAME=PATH")
    a = ap.parse_args()
    rows, parts = build([tuple(x.split("=", 1)) for x in a.inputs])
    if a.expect is not None and len(rows) != a.expect:
        raise SystemExit(f"expected {a.expect} tasks, found {len(rows)}: {({k: v['tasks'] for k, v in parts.items()})}")
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    man = {"total": len(rows), "parts": parts, "combined_sha256": hashlib.sha256(open(a.out, "rb").read()).hexdigest(),
           "note": "frozen executable-eval tasks: never train on, prompt-tune on, or generate candidates for these"}
    json.dump(man, open(a.manifest, "w"), indent=1); print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
