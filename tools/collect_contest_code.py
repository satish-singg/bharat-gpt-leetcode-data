#!/usr/bin/env python3
"""Competition-style SOLUTION code (judge-accepted, TRAIN splits only) -> pipeline JSONL, resumable. CPU + network only; nothing is executed.
Use: tokenizer training (so Scanner / BufferedReader / sys.stdin compress well) and the algorithm part of the corpus. Not the verified SFT data (that is VERIFIED_DATA_PLAN.md).

  python3 tools/collect_contest_code.py --dataset code_contests --lang java   --max-per-problem 8 --out ~/ProjectAI/data/java/contest_java.jsonl
  python3 tools/collect_contest_code.py --dataset code_contests --lang python --max-per-problem 8 --out ~/ProjectAI/data/python/contest_python.jsonl
  python3 tools/collect_contest_code.py --dataset generic --repo <hub id> --solutions-field solutions --lang python --out ...    (APPS/TACO-like: a column holding a list or a JSON string of solution strings; check the card first)

code_contests: deepmind/code_contests train, `solutions` = {language[], solution[]} with language 1 py2, 2 c++, 3 py3, 4 java (card). Only the CORRECT list is read (incorrect_solutions is ignored).
Output line: {"text","source":"code_contest_<lang>","license","doc_id":"<dataset>:<problem index>:<k>","prov":{problem,source_dataset}}.
--max-per-problem caps solutions per problem (the data averages ~88 correct Java solutions per problem; without a cap a few problems would dominate).
The locked evaluation tracks use test splits; this tool reads the train split only and the cleaning step still decontaminates against the locked tasks."""
import argparse, json, os

LANG_CODE = {"python": (3,), "python3": (3,), "java": (4,), "cpp": (2,)}


def code_contests_items(rows, lang, max_per):
    codes = LANG_CODE[lang]
    for i, r in enumerate(rows):
        s = r.get("solutions") or {}
        langs, sols = s.get("language") or [], s.get("solution") or []
        picked = [t for l, t in zip(langs, sols) if l in codes and isinstance(t, str) and t.strip()]
        for k, t in enumerate(picked[:max_per]):
            yield f"code_contests:{i}:{k}", r.get("name"), t


def generic_items(rows, field, max_per, repo):
    for i, r in enumerate(rows):
        v = r.get(field)
        if isinstance(v, str):
            try: v = json.loads(v)
            except ValueError: v = [v]
        for k, t in enumerate([x for x in (v or []) if isinstance(x, str) and x.strip()][:max_per]):
            yield f"{repo}:{i}:{k}", r.get("name") or r.get("problem_id") or i, t


def collect(items, out, lang, n, source_dataset, license_tag="cc-by-4.0", log=print):
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            for line in f:
                try: done.add(json.loads(line)["doc_id"])
                except Exception: pass
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    total = len(done); new = 0
    with open(out, "a", encoding="utf-8") as f:
        for doc_id, problem, text in items:
            if total >= n: break
            if doc_id in done: continue
            f.write(json.dumps({"text": text, "source": f"code_contest_{lang}", "license": license_tag, "doc_id": doc_id,
                                "prov": {"problem": problem, "source_dataset": source_dataset}}, ensure_ascii=False) + "\n")
            total += 1; new += 1
            if new % 50000 == 0: log(f"  {total} solutions")
    return dict(already=len(done), written=new, total_in_file=total)


def stream(repo, split, **kw):
    from datasets import load_dataset
    return load_dataset(repo, split=split, streaming=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=["code_contests", "generic"], required=True); ap.add_argument("--repo", default=None)
    ap.add_argument("--split", default="train"); ap.add_argument("--lang", choices=sorted(LANG_CODE), required=True)
    ap.add_argument("--solutions-field", default="solutions"); ap.add_argument("--max-per-problem", type=int, default=8)
    ap.add_argument("--n", type=int, default=10**9, help="stop when --out holds this many solutions"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.split != "train": raise SystemExit("refusing: only the train split may be collected (test/validation stay out of training)")
    out = os.path.expanduser(a.out)
    if a.dataset == "code_contests":
        repo = a.repo or "deepmind/code_contests"
        items = code_contests_items(stream(repo, a.split), a.lang, a.max_per_problem)
    else:
        if not a.repo: raise SystemExit("--repo is required for --dataset generic")
        repo = a.repo
        items = generic_items(stream(repo, a.split), a.solutions_field, a.max_per_problem, repo)
    print(json.dumps(collect(items, out, "python" if a.lang == "python3" else a.lang, a.n, repo))); print("saved", out)


if __name__ == "__main__":
    main()
