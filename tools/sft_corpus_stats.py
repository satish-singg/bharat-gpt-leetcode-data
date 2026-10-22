#!/usr/bin/env python3
"""Summarise an SFT jsonl built by tools/build_sft_corpus.py: rows and tokens per source / subset / label / language, and prompt+answer token percentiles.
  python3 tools/sft_corpus_stats.py ~/sft_v2/sft_v2.jsonl [--exclude rstar_seed]   (stdlib only; reads the file once)"""
import argparse, collections, json, sys


def stats(lines, exclude=()):
    rows = collections.Counter(); toks = collections.Counter(); by_label = collections.Counter(); by_lang = collections.Counter(); sizes = []
    for line in lines:
        if not line.strip(): continue
        m = json.loads(line)["meta"]
        if m["source_dataset"] in exclude: continue
        key = m["source_dataset"] + (":" + str(m["subset"]) if m.get("subset") else "")
        t = m["prompt_tokens"] + m["answer_tokens"]
        rows[key] += 1; toks[key] += t; by_label[m["label"]] += t; by_lang[m["language"]] += t; sizes.append(t)
    sizes.sort(); q = lambda f: sizes[min(len(sizes) - 1, int(len(sizes) * f))] if sizes else None
    return {"rows": sum(rows.values()), "tokens": sum(toks.values()), "p50_p90_max": [q(.5), q(.9), sizes[-1] if sizes else None],
            "per_source_subset": {k: [rows[k], toks[k]] for k, _ in rows.most_common()}, "tokens_by_label": dict(by_label), "tokens_by_language": dict(by_lang)}


def check_report(lines, report):
    """Rows per source in the file vs 'kept' in the build report -> list of mismatch messages (empty = consistent)."""
    n = collections.Counter(json.loads(l)["meta"]["source_dataset"] for l in lines if l.strip())
    return [f"{k}: report says {v['kept']} rows, file has {n.get(k, 0)}" for k, v in report.get("sources", {}).items() if "kept" in v and n.get(k, 0) != v["kept"]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--exclude", default=""); ap.add_argument("--report", help="build report.json: warn when a source has fewer rows in the file than the report says")
    a = ap.parse_args()
    s = stats(open(a.path, encoding="utf-8"), {x for x in a.exclude.split(",") if x})
    print(json.dumps(s, indent=1))
    if a.report:
        for line in check_report(open(a.path, encoding="utf-8"), json.load(open(a.report))): print("MISMATCH:", line)


if __name__ == "__main__":
    main()
