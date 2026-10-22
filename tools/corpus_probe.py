#!/usr/bin/env python3
"""Read-only probe: how many documents of a cleaned corpus would extra quality rules remove?

It never writes a filtered corpus and changes nothing in the frozen pipeline. cs-v5 is already built and the 124M trunk was trained
on it, so any new rule is a decision for a later corpus (cs-v6) and should be taken only after seeing these numbers on the real data.

Rules (thresholds are flags; the defaults are the common StarCoder-style code heuristics, as far as I know, and a Gopher-style
repetition check for text; adjust them, they are not tuned for this corpus):
  code only   avg_line_long      average non-empty line length > --avg-line (100)
              max_line_long      longest line > --max-line (1000)
              low_alnum          alphanumeric characters < --min-alnum (0.25) of all characters
              data_blob          a run of >= --blob hex or base64 characters (embedded data) (default 200)
  all         license_header     a copyright / license notice in the first 20 lines (informational: not a removal candidate by itself)
              email              an e-mail address (PII candidate)
              ipv4               a dotted IPv4 address (PII candidate)
              dup_lines          more than --dup-lines (0.30) of the non-empty lines are repeats of an earlier line

  python3 tools/corpus_probe.py clean/train.jsonl --max-docs 200000 --out probe_report.json
"""
import argparse
import collections
import json
import re
import sys

HEX_B64 = re.compile(r"[A-Za-z0-9+/=]{%d,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
LICENSE_HEAD = re.compile(r"copyright|licensed under|all rights reserved|spdx-license-identifier|permission is hereby granted", re.I)
RULES = ("avg_line_long", "max_line_long", "low_alnum", "data_blob", "dup_lines", "email", "ipv4", "license_header")
REMOVAL_CANDIDATES = ("avg_line_long", "max_line_long", "low_alnum", "data_blob", "dup_lines")   # PII and headers are not removals


def is_code(source):
    return str(source or "").startswith("code_")


def probe_doc(text, source, avg_line=100, max_line=1000, min_alnum=0.25, blob=200, dup_lines=0.30):
    """-> set of rule names this document trips."""
    hits = set()
    lines = [l for l in text.split("\n") if l.strip()]
    if lines:
        seen, dup = set(), 0
        for l in lines:
            s = l.strip()
            if s in seen:
                dup += 1
            seen.add(s)
        if len(lines) >= 10 and dup / len(lines) > dup_lines:
            hits.add("dup_lines")
    if is_code(source):
        if lines and sum(map(len, lines)) / len(lines) > avg_line:
            hits.add("avg_line_long")
        if max(map(len, text.split("\n")), default=0) > max_line:
            hits.add("max_line_long")
        if text and sum(c.isalnum() for c in text) / len(text) < min_alnum:
            hits.add("low_alnum")
        if re.search(HEX_B64.pattern % blob, text):
            hits.add("data_blob")
    if LICENSE_HEAD.search("\n".join(text.split("\n")[:20])):
        hits.add("license_header")
    if EMAIL.search(text):
        hits.add("email")
    if IPV4.search(text):
        hits.add("ipv4")
    return hits


def run(paths, max_docs=None, stride=1, examples=3, **thr):
    per = collections.defaultdict(lambda: {"docs": 0, "chars": 0, "removal_candidates": 0, "removal_candidate_chars": 0,
                                           "rules": collections.Counter(), "examples": collections.defaultdict(list)})
    n = 0
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if stride > 1 and i % stride:
                    continue
                if not line.strip():
                    continue
                r = json.loads(line)
                t, src = r.get("text", ""), r.get("source", "unknown")
                hits = probe_doc(t, src, **thr)
                s = per[src]
                s["docs"] += 1
                s["chars"] += len(t)
                for h in hits:
                    s["rules"][h] += 1
                    if len(s["examples"][h]) < examples:
                        s["examples"][h].append(r.get("doc_id"))
                if hits & set(REMOVAL_CANDIDATES):
                    s["removal_candidates"] += 1
                    s["removal_candidate_chars"] += len(t)
                n += 1
                if max_docs and n >= max_docs:
                    break
        if max_docs and n >= max_docs:
            break
    out = {"docs_probed": n, "thresholds": thr, "sources": {}}
    for src, s in sorted(per.items()):
        d = max(1, s["docs"])
        out["sources"][src] = {"docs": s["docs"], "chars": s["chars"],
                               "pct_docs_removal_candidates": round(100 * s["removal_candidates"] / d, 3),
                               "pct_chars_removal_candidates": round(100 * s["removal_candidate_chars"] / max(1, s["chars"]), 3),
                               "pct_by_rule": {k: round(100 * v / d, 3) for k, v in sorted(s["rules"].items())},
                               "examples": {k: v for k, v in s["examples"].items()}}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--max-docs", type=int, default=None)
    ap.add_argument("--stride", type=int, default=1, help="read every Nth line (a cheap sample across the whole file)")
    ap.add_argument("--avg-line", type=int, default=100); ap.add_argument("--max-line", type=int, default=1000)
    ap.add_argument("--min-alnum", type=float, default=0.25); ap.add_argument("--blob", type=int, default=200)
    ap.add_argument("--dup-lines", type=float, default=0.30)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = run(a.files, a.max_docs, a.stride, avg_line=a.avg_line, max_line=a.max_line, min_alnum=a.min_alnum, blob=a.blob, dup_lines=a.dup_lines)
    txt = json.dumps(rep, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
