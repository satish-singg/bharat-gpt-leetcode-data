#!/usr/bin/env python3
"""Validate a hand-collected "gold" set (ChatGPT / Gemini / human answers) before it goes anywhere near training.

  python3 tools/gold_set_check.py --in gold.jsonl --out gold_clean.jsonl [--locked eval_tasks_all.jsonl] [--report gold_report.json]

One JSON per line:
  {"id": "g0001", "source": "chatgpt|gemini|human|other", "language": "python|java|sql|text", "topic": "graphs/bfs",
   "instruction": "...", "response": "...explanation... ```python ...code... ```",
   "tests": [{"stdin": "...", "stdout": "..."}]        <- optional; if present the code is RUN (needs the sandbox gate) and must pass all
   "model_note": "free text, e.g. 'GPT-5 thinking, 2026-10-20'"}
Rejects (and says why): missing fields, bad source/language, no code block when language is python/java, duplicate id or instruction,
instruction/response overlapping a locked eval task (--locked; rule shared with build_sft_corpus: instruction shares >=20% of a locked prompt's 8-grams, or the response shares a distinctive 13-gram of a locked reference), tests present but failing.
Rows that survive get label "gold_checked" (tests ran) or "gold_unchecked" (no tests). Neither is the same as test_verified from datasets.
"""
import argparse, hashlib, json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "eval_framework" / "exec_track"), str(HERE.parent / "eval_framework")]

SOURCES = {"chatgpt", "gemini", "human", "other"}
LANGS = {"python", "java", "sql", "text"}
CODE_LANGS = {"python", "java"}


def has_code(resp):
    return bool(re.search(r"```[a-zA-Z0-9+#]*\n.+?```", resp, re.S))


def check(rows, locked=None, run_tests=None):
    """run_tests(language, response, tests) -> (passed, total). Injected so the logic is testable without a sandbox."""
    import build_sft_corpus as B
    import overlap as O
    idx = B.locked_from_tasks(locked) if locked else None      # same rule as the SFT build: 8-gram prompt containment + distinctive solution 13-grams (idioms do not count)
    # short locked prompts (< 20 8-grams) are not indexed by that rule, so keep a strict check of the INSTRUCTION only: any verbatim 13-gram of a locked prompt
    pidx13 = {g for g, hits in (O.fingerprints(locked)[0] if locked else {}).items() if any(part == "prompt" for _, part in hits)}
    kept, rej, seen_id, seen_ins = [], [], set(), set()

    def bad(r, why): rej.append({"id": r.get("id"), "why": why})
    for r in rows:
        miss = [k for k in ("id", "source", "language", "instruction", "response") if not isinstance(r.get(k), str) or not r.get(k).strip()]
        if miss: bad(r, "missing:" + ",".join(miss)); continue
        if r["source"] not in SOURCES: bad(r, "bad_source"); continue
        if r["language"] not in LANGS: bad(r, "bad_language"); continue
        if r["language"] in CODE_LANGS and not has_code(r["response"]): bad(r, "no_code_block"); continue
        key = hashlib.sha256(re.sub(r"\s+", " ", r["instruction"]).strip().lower().encode()).hexdigest()
        if r["id"] in seen_id: bad(r, "duplicate_id"); continue
        if key in seen_ins: bad(r, "duplicate_instruction"); continue
        if idx and (B.overlap_reason(r["instruction"], r["response"], idx) or any(g in pidx13 for g in O._grams(r["instruction"]))): bad(r, "locked_overlap"); continue
        label = "gold_unchecked"
        if r.get("tests"):
            if run_tests is None: bad(r, "tests_present_but_no_sandbox"); continue
            p, t = run_tests(r["language"], r["response"], r["tests"])
            if p != t: bad(r, f"tests_failed:{p}/{t}"); continue
            label = "gold_checked"
        seen_id.add(r["id"]); seen_ins.add(key)
        kept.append({**r, "label": label, "response_sha256": hashlib.sha256(r["response"].encode()).hexdigest()})
    return kept, rej


def _runner():
    import sandbox_gate as SG
    SG.require()
    from runners.code_runner import run_code
    def f(language, response, tests):
        res = run_code({"language": language, "tests": json.dumps([{"name": f"t{i}", "stdin": t.get("stdin", ""), "stdout": t["stdout"]} for i, t in enumerate(tests)]),
                        "time_limit_s": 10, "item_timeout_s": 60}, response)
        d = res["details"]; return d.get("passed", 0), d.get("total", len(tests))
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True); ap.add_argument("--locked"); ap.add_argument("--report")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    locked = [json.loads(l) for l in open(a.locked, encoding="utf-8") if l.strip()] if a.locked else None
    runner = _runner() if any(r.get("tests") for r in rows) else None
    kept, rej = check(rows, locked, runner)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in kept: f.write(json.dumps(r) + "\n")
    why = {}
    for r in rej: why[r["why"].split(":")[0]] = why.get(r["why"].split(":")[0], 0) + 1
    rep = {"in": len(rows), "kept": len(kept), "rejected": len(rej), "by_reason": why, "kept_by_label": {l: sum(k["label"] == l for k in kept) for l in ("gold_checked", "gold_unchecked")},
           "locked_checked": bool(locked), "rejected_rows": rej[:50]}
    print(json.dumps(rep, indent=1))
    if a.report: json.dump(rep, open(a.report, "w"), indent=1)
    if not locked: print("\nNOTE: no --locked file given, so overlap with the 1,365 locked eval tasks was NOT checked.")


if __name__ == "__main__":
    main()
