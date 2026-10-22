#!/usr/bin/env python3
"""Yield audit: how many UNIQUE, USABLE tokens will a collected source give once filters and dedup are applied?  CPU only, read-only.

  python3 tools/yield_audit.py --tokenizer data/tokens/tokenizer/tokenizer.json --out results/yield_audit.json \
      --file python=data/python/stack_edu_python.jsonl:900000 --file java=data/java/stack_edu_java.jsonl:800000 ...
  --file GROUP=PATH[:PLANNED_DOCS]   GROUP is python|java|other|math|text (used to compare with the targets); PLANNED_DOCS = how many documents the full collection will have
Per file: documents read, dropped by rule (empty/short, StarCoder-style code rules from tools/corpus_probe.py, Python `ast.parse` failure, exact duplicate -
within the file AND against every file seen before it), mean tokens per kept document, then a projection:
    projected unique tokens = PLANNED_DOCS x (kept share) x (mean tokens per kept document).
The projection is OPTIMISTIC: duplicates grow with scale and near-duplicates (MinHash) are not measured here; read it as an upper bound. Then groups are compared
with the targets of docs/FINAL_PLAN.md and a SHORT flag is printed where the projection is under the target."""
import argparse, ast, collections, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus_probe as CP

TARGETS_B = {"python": 2.0, "java": 2.4, "other": 1.0, "math": 0.75, "text": 1.7}     # unique tokens after cleaning, billions (docs/FINAL_PLAN.md)
DROP_RULES = ("dup_lines", "avg_line_long", "max_line_long", "low_alnum", "data_blob")  # corpus_probe rules treated as drops (license/email/ip are only counted)
WS = re.compile(r"\s+")


def fingerprint(text):
    return hashlib.sha1(WS.sub(" ", text).strip().encode("utf-8", "ignore")).hexdigest()[:16]


def audit_file(docs, count_tokens, seen, is_code, is_python, planned=None, min_chars=64):
    c = collections.Counter(); tok_kept = 0; n = 0
    for text in docs:
        n += 1
        if not isinstance(text, str) or len(text.strip()) < min_chars: c["empty_or_short"] += 1; continue
        hits = CP.probe_doc(text, "code_x" if is_code else "text_x")
        bad = [h for h in DROP_RULES if h in hits]
        if bad: c["rule_" + bad[0]] += 1; continue
        if is_python:
            try: ast.parse(text)
            except (SyntaxError, ValueError, MemoryError, RecursionError): c["python_syntax"] += 1; continue
        fp = fingerprint(text)
        if fp in seen: c["exact_duplicate"] += 1; continue
        seen.add(fp); tok_kept += count_tokens(text); c["kept"] += 1
        for h in ("license_header", "email", "ipv4"):
            if h in hits: c["note_" + h] += 1
    kept = c["kept"]; share = kept / n if n else 0; tpd = tok_kept / kept if kept else 0
    rep = {"docs_read": n, "kept": kept, "kept_share": round(share, 4), "mean_tokens_per_kept_doc": round(tpd, 1), "kept_tokens": tok_kept,
           "counts": dict(c)}
    if planned: rep["planned_docs"] = planned; rep["projected_unique_tokens_B"] = round(planned * share * tpd / 1e9, 3)
    return rep


def read_texts(path, limit):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit: break
            try: yield json.loads(line).get("text")
            except ValueError: continue


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--file", action="append", required=True); ap.add_argument("--max-docs", type=int, default=50000)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); count = lambda t: len(tk.encode(t).ids)
    seen = set(); report = {}; groups = collections.defaultdict(float)
    for spec in a.file:
        name, rest = spec.split("=", 1); group = name.split(":")[0]
        path, _, planned = rest.partition(":")
        is_code = group in ("python", "java", "other"); is_py = group == "python" or "python" in os.path.basename(path)
        rep = audit_file(read_texts(path, a.max_docs), count, seen, is_code, is_py, int(planned) if planned else None)
        report[os.path.basename(path)] = {"group": group, **rep}
        groups[group] += rep.get("projected_unique_tokens_B", 0)
        print(f"{os.path.basename(path):34s} read {rep['docs_read']:>7} kept {rep['kept_share']*100:5.1f}%  {rep['mean_tokens_per_kept_doc']:7.1f} tok/doc  projected {rep.get('projected_unique_tokens_B', '-')} B  {rep['counts']}")
    print("\ngroup      projected(B)  target(B)")
    for g, tgt in TARGETS_B.items():
        have = round(groups.get(g, 0), 3); print(f"{g:9s}  {have:>9}  {tgt:>8}   {'SHORT' if g in groups and have < tgt else ''}")
    report["_groups_projected_B"] = dict(groups); report["_targets_B"] = TARGETS_B
    os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(a.out))), exist_ok=True)
    json.dump(report, open(os.path.expanduser(a.out), "w"), indent=1); print("saved", a.out)


if __name__ == "__main__":
    main()
