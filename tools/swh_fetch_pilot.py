#!/usr/bin/env python3
"""Pilot: fetch a small random sample of Stack-Edu / python-edu files from the Software Heritage S3 bucket and measure speed and content.
CPU only, network needed on THIS machine (the owner's JioPC); nothing is executed. Read-only except the optional --out file.

  python3 tools/swh_fetch_pilot.py --repo HuggingFaceTB/stack-edu --config Python --n 2000 --min-score 3 \
      --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --out ~/swh_python_pilot.json [--save-jsonl ~/swh_python_2000.jsonl]
  (python-edu is the 'python-edu' config of HuggingFaceTB/smollm-corpus; Stack-Edu configs: C CSharp Cpp Go Java JavaScript Markdown PHP Python Ruby Rust SQL Shell Swift TypeScript)

The card tables list only blob_ids; the file text is at https://softwareheritage.s3.amazonaws.com/content/<blob_id> (gzip). The card says the full
Python fetch takes about 6 h on a 16-core AWS us-east-1 machine, so what matters here is files/second from YOUR network, the failure rate, and
the token yield per file. Decoding follows the card (src_encoding, errors='ignore'); the number of files with a decode problem is not detectable
that way, so it is not reported. Missing blobs are counted, never retried more than twice.
Report: attempted / fetched / failures by cause, seconds and files per second, projected hours for 100k and 1M files, token stats and exact-duplicate
rate (java_pilot.analyze), and the share of tokens per int_score.
"""
import argparse, collections, concurrent.futures as cf, gzip, json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import java_pilot as P

URL = "https://softwareheritage.s3.amazonaws.com/content/{}"


def http_get(blob_id, timeout=30):
    req = urllib.request.Request(URL.format(blob_id), headers={"User-Agent": "bharat-gpt-pilot"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def decode_blob(raw_gz, encoding=None):
    return gzip.decompress(raw_gz).decode(encoding or "utf-8", errors="ignore")


def fetch_one(row, getter=http_get, retries=2):
    """(row, text or None, error string or None)"""
    err = "unknown"
    for attempt in range(retries + 1):
        try:
            return row, decode_blob(getter(row["blob_id"]), row.get("src_encoding")), None
        except urllib.error.HTTPError as e:
            err = f"http_{e.code}"
            if e.code in (403, 404): break            # missing / not allowed: retrying will not help
        except LookupError:
            err = "bad_encoding"; break
        except Exception as e:                        # timeouts, resets, bad gzip
            err = type(e).__name__
    return row, None, err


def fetch_all(rows, workers=32, getter=http_get):
    t0 = time.time()
    ok, errs = [], collections.Counter()
    with cf.ThreadPoolExecutor(workers) as ex:
        for row, text, err in ex.map(lambda r: fetch_one(r, getter), rows):
            if text is None: errs[err] += 1
            else: ok.append((row, text))
    return ok, errs, time.time() - t0


def sample_rows(repo, config, n, min_score, seed=0, scan_limit=2_000_000):
    from datasets import load_dataset
    ds = load_dataset(repo, config, split="train", streaming=True).shuffle(seed=seed, buffer_size=100_000)
    out = []
    for i, r in enumerate(ds):
        if i >= scan_limit: break
        if r.get("int_score") is not None and r["int_score"] < min_score: continue
        out.append({k: r.get(k) for k in ("blob_id", "repo_name", "path", "src_encoding", "int_score", "length_bytes", "detected_licenses", "language")})
        if len(out) >= n: break
    return out


def summarize(ok, errs, secs, attempted, tokenizer=None, workers=32):
    stats = P.analyze((t for _, t in ok), tokenizer, limit=len(ok) or 1)
    per_score = collections.Counter()
    if tokenizer is not None:
        for row, t in ok: per_score[row.get("int_score")] += len(tokenizer.encode(t).ids)
    fps = len(ok) / secs if secs else 0
    return {"attempted": attempted, "fetched": len(ok), "failures": dict(errs), "seconds": round(secs, 1), "workers": workers,
            "files_per_second": round(fps, 2),
            "projected_hours_100k_files": round(100_000 / fps / 3600, 2) if fps else None,
            "projected_hours_1M_files": round(1_000_000 / fps / 3600, 2) if fps else None,
            "tokens_by_int_score": dict(per_score), "content": stats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="HuggingFaceTB/stack-edu"); ap.add_argument("--config", required=True)
    ap.add_argument("--n", type=int, default=2000); ap.add_argument("--min-score", type=int, default=3)
    ap.add_argument("--workers", type=int, default=32); ap.add_argument("--tokenizer"); ap.add_argument("--out", required=True)
    ap.add_argument("--save-jsonl", help="also keep the fetched files with provenance (blob_id, repo, path, score, licenses)")
    a = ap.parse_args()
    tk = None
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer))
    rows = sample_rows(a.repo, a.config, a.n, a.min_score)
    print(f"sampled {len(rows)} rows of {a.repo}/{a.config} with int_score >= {a.min_score}", flush=True)
    ok, errs, secs = fetch_all(rows, a.workers)
    rep = summarize(ok, errs, secs, len(rows), tk, a.workers)
    rep.update(repo=a.repo, config=a.config, min_score=a.min_score)
    print(json.dumps({k: v for k, v in rep.items() if k != "content"}, indent=1))
    print(json.dumps({k: v for k, v in rep["content"].items() if k != "previews"}, indent=1))
    json.dump(rep, open(os.path.expanduser(a.out), "w"), indent=1)
    if a.save_jsonl:
        with open(os.path.expanduser(a.save_jsonl), "w") as f:
            for row, t in ok: f.write(json.dumps({**row, "text": t}, ensure_ascii=False) + "\n")
    print("saved", a.out)


if __name__ == "__main__":
    main()
