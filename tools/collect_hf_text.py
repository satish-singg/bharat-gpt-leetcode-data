#!/usr/bin/env python3
"""Stream N documents of a Hugging Face text dataset into pipeline JSONL, resumable. CPU + network only.

  python3 tools/collect_hf_text.py --repo HuggingFaceTB/finemath --config finemath-4plus --n 400000 --source math_finemath --out ~/ProjectAI/data/math/finemath4.jsonl
  python3 tools/collect_hf_text.py --repo open-web-math/open-web-math --n 100000 --source math_owm --out ~/ProjectAI/data/math/owm.jsonl
Output line: {"text","source","license","doc_id":"<repo>:<index>"}.  A fixed --seed gives a fixed shuffled order; a stopped run continues after the lines already written.
FineMath-4plus was better than other math sets in SmolLM2's annealing ablations (about 2x GSM8K, 6x MATH vs InfiMM-WebMath)."""
import argparse, json, os


def collect(docs, out, source, repo, n, license_tag, min_chars, max_chars, log=print):
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            for line in f:
                try: done.add(json.loads(line)["doc_id"])
                except Exception: pass
    have = len(done)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    seen = written = short = 0
    with open(out, "a", encoding="utf-8") as f:
        for i, d in enumerate(docs):
            if have + written >= n: break
            if f"{repo}:{i}" in done: continue          # same seed = same order: documents written by an earlier run are skipped by id
            t = d if isinstance(d, str) else None
            if not t or len(t) < min_chars: short += 1; continue
            f.write(json.dumps({"text": t[:max_chars], "source": source, "license": license_tag, "doc_id": f"{repo}:{i}"}, ensure_ascii=False) + "\n"); written += 1
            if written % 20000 == 0: log(f"  {have + written} docs")
    return dict(already=have, written=written, skipped_short=short, total_in_file=have + written)


def stream_texts(repo, config, split, field, seed):
    from datasets import load_dataset
    ds = load_dataset(repo, config, split=split, streaming=True) if config else load_dataset(repo, split=split, streaming=True)
    for r in ds.shuffle(seed=seed, buffer_size=50_000):
        yield r.get(field)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True); ap.add_argument("--config", default=None); ap.add_argument("--split", default="train"); ap.add_argument("--field", default="text")
    ap.add_argument("--n", type=int, required=True); ap.add_argument("--source", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--license-tag", default="odc-by"); ap.add_argument("--min-chars", type=int, default=200); ap.add_argument("--max-chars", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    st = collect(stream_texts(a.repo, a.config, a.split, a.field, a.seed), out, a.source, a.repo, a.n, a.license_tag, a.min_chars, a.max_chars)
    print(json.dumps(st)); print("saved", out)


if __name__ == "__main__":
    main()
