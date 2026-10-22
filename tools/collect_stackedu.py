#!/usr/bin/env python3
"""Collect Stack-Edu files (HuggingFaceTB/stack-edu) for one language into pipeline JSONL, resumable. CPU + network (Software Heritage S3), nothing is executed.

  python3 tools/collect_stackedu.py --config Python --n 300000 --min-score 3 --source code_python_edu --out ~/ProjectAI/data/python/stack_edu_python.jsonl
  (configs: Python Java Cpp JavaScript TypeScript Go Rust CSharp Shell SQL ...; Java's educational threshold in SmolLM2 was 2, the others 3)

Output line: {"text","source","license","doc_id":"sh:<blob_id>","url","prov":{repo,path,score,header_stripped}}.  Same input + same --seed = same order, so
a stopped run continues where it ended (doc_ids already in --out are skipped and counted toward --n).
What it does to each file:
  * drops judge-style repos/paths (leetcode, hackerrank, codeforces, atcoder, kattis, lintcode): policy decided 2026-10-21 (--exclude-regex "" to disable)
  * strips a leading license/copyright comment block (OpenCoder removes copyright notices; ~35% of Java files start with one)
  * nothing else: length, language, quality and duplicate filters belong to the cleaning step (scale_clean.py)."""
import argparse, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swh_fetch_pilot as S

JUDGE_RE = r"leetcode|leet_code|lintcode|codeforces|hackerrank|kattis|atcoder"
LICENSE_WORD = re.compile(r"copyright|license|licence|spdx|all rights reserved|permission is hereby granted", re.I)


def strip_license_header(text):
    """Remove ONE leading comment block (/* ... */ or a run of // or # lines) when it mentions a license/copyright. Returns (text, stripped?)."""
    s = text.lstrip("﻿")
    m = re.match(r"\s*/\*.*?\*/[ \t]*\r?\n?", s, re.S)
    if not m:
        m = re.match(r"(?:[ \t]*(?://|#)[^\n]*\n)+", s)
        if m and s.startswith("#!"): return text, False          # shebang line is code, keep
    if m and LICENSE_WORD.search(m.group(0)):
        return s[m.end():].lstrip("\n"), True
    return text, False


def excluded(row, pattern):
    return bool(pattern) and bool(re.search(pattern, f"{row.get('repo_name') or ''} {row.get('path') or ''}", re.I))


def already_done(out):
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            for line in f:
                try: done.add(json.loads(line)["doc_id"])
                except Exception: pass
    return done


def collect(rows, getter, out, source, n, exclude_pattern=JUDGE_RE, workers=32, chunk=2000, log=print):
    """rows: iterable of Stack-Edu table rows. Returns counters. Appends to `out`."""
    done = already_done(out); stats = dict(already=len(done), written=0, excluded=0, fetch_failed=0, stripped=0)
    total = len(done); t0 = time.time(); buf = []
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    def flush(f, batch):
        nonlocal total
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(workers) as ex:
            for row, text, err in ex.map(lambda r: S.fetch_one(r, getter), batch):
                if text is None: stats["fetch_failed"] += 1; continue
                text, st = strip_license_header(text); stats["stripped"] += st
                if not text.strip(): continue
                f.write(json.dumps({"text": text, "source": source, "license": ",".join(row.get("detected_licenses") or []) or "unknown",
                                    "doc_id": "sh:" + row["blob_id"], "url": S.URL.format(row["blob_id"]),
                                    "prov": {"repo": row.get("repo_name"), "path": row.get("path"), "score": row.get("int_score"), "header_stripped": bool(st)}},
                                   ensure_ascii=False) + "\n")
                stats["written"] += 1; total += 1
        f.flush(); log(f"  {total} files ({stats['written']} new) in {time.time()-t0:.0f}s, fetch failures {stats['fetch_failed']}")

    with open(out, "a", encoding="utf-8") as f:
        for row in rows:
            if total + len(buf) >= n: break
            if "sh:" + row["blob_id"] in done: continue
            if excluded(row, exclude_pattern): stats["excluded"] += 1; continue
            buf.append(row)
            if len(buf) >= chunk: flush(f, buf); buf = []
        if buf and total < n: flush(f, buf[: n - total])
    stats["total_in_file"] = total
    return stats


def stream_rows(repo, config, min_score, seed):
    from datasets import load_dataset
    ds = load_dataset(repo, config, split="train", streaming=True).shuffle(seed=seed, buffer_size=100_000)
    for r in ds:
        if r.get("int_score") is not None and r["int_score"] < min_score: continue
        yield {k: r.get(k) for k in ("blob_id", "repo_name", "path", "src_encoding", "int_score", "length_bytes", "detected_licenses", "language")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="HuggingFaceTB/stack-edu"); ap.add_argument("--config", required=True)
    ap.add_argument("--n", type=int, required=True, help="stop when --out holds this many files"); ap.add_argument("--min-score", type=int, default=3)
    ap.add_argument("--source", required=True, help="value of the `source` field, e.g. code_python_edu (code_* sources get FIM and the code filters)")
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=32); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--exclude-regex", default=JUDGE_RE)
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    st = collect(stream_rows(a.repo, a.config, a.min_score, a.seed), S.http_get, out, a.source, a.n, a.exclude_regex, a.workers)
    print(json.dumps(st)); print("saved", out)


if __name__ == "__main__":
    main()
