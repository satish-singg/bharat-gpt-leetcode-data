#!/usr/bin/env python3
"""Draw a random sample of documents per `source` from a big cleaned JSONL (reservoir sampling, one pass, small memory).
Use it to make the per-domain samples that tools/tokenizer_study.py needs.

  python3 tools/sample_by_source.py --in ~/cs-data/cs-v5/clean/train.jsonl --out-dir ~/tok_samples --per-source 2000 [--seed 1]

Writes <out-dir>/<source>.jsonl, each line {"text": ..., "source": ...}. Read-only on the input. Note: `code_java_sql_js` is ONE source;
split it by language yourself if you need per-language numbers."""
import argparse, json, pathlib, random


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--per-source", type=int, default=2000); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed); res, seen = {}, {}
    with open(a.inp, encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try: d = json.loads(line)
            except ValueError: continue
            s, t = d.get("source", "unknown"), d.get("text")
            if not isinstance(t, str) or not t: continue
            n = seen[s] = seen.get(s, 0) + 1; r = res.setdefault(s, [])
            if len(r) < a.per_source: r.append(t)
            else:
                j = rng.randrange(n)
                if j < a.per_source: r[j] = t
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    for s, r in res.items():
        with open(out / f"{s}.jsonl", "w", encoding="utf-8") as f:
            for t in r: f.write(json.dumps({"text": t, "source": s}, ensure_ascii=False) + "\n")
        print(f"{s}: sampled {len(r)} of {seen[s]} documents")


if __name__ == "__main__":
    main()
