#!/usr/bin/env python3
"""Turn TRAIN-split exec-track tasks into prompts for the Kaggle generator. Only the statement leaves this machine: NO tests, NO reference.

  python3 tools/make_candidate_prompts.py --tasks train_tasks.jsonl --out prompts.jsonl [--limit 300] [--seed 1]

Refuses any task whose source.split is not "train" (audit 2026-10-20). Output rows: {"id", "language", "messages": [...], "template_sha256"}.
Upload prompts.jsonl to Kaggle as a Dataset (Add Data -> Upload). The template text below is hashed into every candidate it produces.
"""
import argparse, hashlib, json, random, sys

SYSTEM = "You are an expert programmer. You write correct, efficient, readable solutions and you handle edge cases."
TEMPLATES = {
    "stdio:python": "Solve the following problem with a complete Python 3 program. Read from standard input and write to standard output.\n"
                    "Think about edge cases and time limits first. Reply with ONE ```python code block and nothing after it.\n\nProblem:\n{statement}\n",
    "stdio:java": "Solve the following problem with a complete Java program. The public class MUST be named Main. Read from standard input "
                  "and write to standard output. Use fast input for large data. Reply with ONE ```java code block and nothing after it.\n\nProblem:\n{statement}\n",
    "leetcode": "Complete the Python class below so that it solves the problem. Keep the given class and method names. "
                "Reply with ONE ```python code block containing the full class and nothing after it.\n\n{statement}\n",
}
TEMPLATE_SHA = hashlib.sha256((SYSTEM + json.dumps(TEMPLATES, sort_keys=True)).encode()).hexdigest()


def kind_of(t):
    if t.get("track") == "leetcode":
        return "leetcode"
    return "stdio:java" if (t.get("language") or "python").lower() == "java" else "stdio:python"


def build(tasks, limit=None, seed=1):
    bad = [t["id"] for t in tasks if (t.get("source") or {}).get("split") != "train" and t.get("split") != "train"]
    if bad:
        raise SystemExit(f"{len(bad)} task(s) are not labelled split=train (first: {bad[0]}). Rebuild them with export-parquet --split train.")
    tasks = list(tasks)
    random.Random(seed).shuffle(tasks)
    rows = []
    for t in tasks[: limit or len(tasks)]:
        k = kind_of(t)
        rows.append({"id": t["id"], "language": t.get("language") or "python",
                     "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": TEMPLATES[k].format(statement=t.get("prompt", ""))}],
                     "template_sha256": TEMPLATE_SHA})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.tasks, encoding="utf-8") if l.strip()]
    rows = build(tasks, a.limit, a.seed)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} prompts to {a.out}; template sha256 {TEMPLATE_SHA[:16]}...")


if __name__ == "__main__":
    main()
