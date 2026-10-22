#!/usr/bin/env python3
"""Token-length distribution of documents or SFT rows: decides 2,048 vs 4,096 context from data.  CPU only, read-only.

  python3 tools/context_stats.py --tokenizer TOKENIZER.json --file python=data/python/stack_edu_python.jsonl --file sft=data/training/lc_repos.jsonl --fields question,answer
--fields joins several fields (SFT rows); default is the single field `text`.  Prints percentiles and the share of rows LONGER than 1,024 / 2,048 / 4,096 / 8,192 tokens.
Rule of thumb in docs/FINAL_PLAN.md: SFT/verified records > 2,048 tokens above ~10-20% means the context goes to 4,096 (pretraining documents are cut into windows, so for them
the length matters only for how much of a file fits in one window)."""
import argparse, json, os

CUTS = (1024, 2048, 4096, 8192)


def stats(lengths):
    xs = sorted(lengths); n = len(xs)
    if not n: return {"n": 0}
    pct = lambda p: xs[min(n - 1, int(p * n))]
    return {"n": n, "mean": round(sum(xs) / n, 1), "p50": pct(0.5), "p90": pct(0.9), "p95": pct(0.95), "p99": pct(0.99),
            "share_over": {str(c): round(sum(1 for x in xs if x > c) / n, 4) for c in CUTS}}


def read(path, fields, limit):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit: break
            try: d = json.loads(line)
            except ValueError: continue
            parts = [d.get(k) for k in fields]
            if all(isinstance(p, str) for p in parts): yield "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--file", action="append", required=True)
    ap.add_argument("--fields", default="text"); ap.add_argument("--limit", type=int, default=20000); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); fields = a.fields.split(","); res = {}
    for spec in a.file:
        name, path = spec.split("=", 1)
        res[name] = stats([len(tk.encode(t).ids) for t in read(path, fields, a.limit)])
        print(name, json.dumps(res[name]))
    if a.out: json.dump(res, open(os.path.expanduser(a.out), "w"), indent=1)


if __name__ == "__main__":
    main()
