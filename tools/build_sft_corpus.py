#!/usr/bin/env python3
"""Build ONE clean SFT file from the sources we measured (tools/sft_pilot.py), with full per-source accounting. CPU only.

  env -u PYTHONPATH ~/pilot-venv2/bin/python -u tools/build_sft_corpus.py --sources opc_edu,kodcode,rstar_seed,gretel,opc_mceval \
      --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --locked ~/locked_eval_1365.jsonl --out ~/sft_v2/sft_v2.jsonl --report ~/sft_v2/report.json \
      [--cap kodcode=150000] [--kod-subsets Prefill,Filter,Docs,Algorithm,Data_Structure,Package,Evol] [--kod-min-pass 0.3]

Reads each dataset's parquet files in full, in small column-projected batches (flat memory; files are cached by huggingface_hub). --append adds sources to an existing output.
Output row = the format of phase0/sft/sft_data.py: {"text": "Question: <Q>\\n\\nAnswer:\\n<A>", "prov": {...}, "meta": {...}}.
Per-source rules (each drop is counted):
  all     : empty, special-token string in text, Q or A containing the Q/A separator, prompt+answer tokens + 16 > --max-tokens (never truncated),
            duplicate normalized prompt (first kept; with --one-per-prompt semantics for rStar's many solutions), Python fence that does not parse,
            locked_overlap = row PROMPT shares >=20% of a locked task's prompt 8-grams  OR  >=1 verbatim 13-gram of the SOLUTION that is distinctive (in <=3 locked tasks)
            with a locked reference solution of >=60 words (idioms are NOT counted: the old prompt+solution 13-gram rule dropped ~5% of KodCode for shared idioms).
  kodcode : subset in --kod-subsets (default excludes Taco, Code_Contests, Apps, Leetcode, Codeforces: same problem pools as the locked tasks),
            gpt_pass_percentage >= --kod-min-pass, benchmark_similarity < 0.8 (KodCode's own closeness to HumanEval/MBPP/BigCodeBench/LiveCodeBench).
  rstar   : verified and is_passed both true. opc_edu / opc_mceval / gretel : as measured; gretel drops INSERT statements from the schema.
Labels: nothing here is test_verified. kodcode/rstar/opc_edu carry "self_tested" (the solution passed tests written by the same pipeline, NOT independent);
opc_mceval/gretel carry "unverified_distill". Do not upgrade a label without running the tests ourselves (tools/gold_set_check.py)."""
import argparse, hashlib, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sft_pilot as P
import hf_sft_adapter as A

SEP = "\n\nAnswer:\n"
KOD_DEFAULT = ["Prefill", "Filter", "Docs", "Algorithm", "Data_Structure", "Package", "Evol"]
INSERT = re.compile(r"\bINSERT\s+INTO\b.*?;", re.S | re.I)


def fence(lang, code):
    return f"```{lang}\n{(code or '').strip()}\n```"


def to_qa(name, r):
    """-> (question, answer, lang, label, key, meta_extra) or None (with reason in a 2-tuple ("drop", reason))."""
    if name == "kodcode":
        return r["question"], fence("python", r["solution"]), "python", "self_tested", r.get("question_id"), {"subset": r.get("subset")}
    if name == "opc_edu":
        return r["instruction"], fence("python", r["code"]), "python", "self_tested", r.get("seq_id"), {}
    if name == "rstar_seed":
        return r["question"], fence("python", r["code"]), "python", "self_tested", r.get("question_id"), {}
    if name == "gretel":
        ctx = INSERT.sub("", r.get("sql_context") or "").strip()
        return (ctx + "\n\n" + (r.get("sql_prompt") or "")).strip(), fence("sql", r["sql"]), "sql", "unverified_distill", r.get("id"), {}
    if name == "opc_mceval":
        return r["instruction"], (r.get("output") or "").strip(), P._fence_lang(r.get("output")), "unverified_distill", None, {}
    if name in ("leetcode", "leetcode_resp"):
        q = ((r.get("problem_description") or "").strip() + "\n\nStarter code:\n" + fence("python", r.get("starter_code"))).strip()
        if name == "leetcode":     # the reference solution of the dataset (its authors ran it against their tests; we did not)
            return q, fence("python", r.get("completion")), "python", "self_tested", r.get("task_id"), {"difficulty": r.get("difficulty"), "date": str(r.get("estimated_date"))[:10]}
        return q, (r.get("response") or "").strip(), "python", "unverified_distill", r.get("task_id"), {"difficulty": r.get("difficulty"), "date": str(r.get("estimated_date"))[:10]}
    raise SystemExit("unknown source " + name)


def row_ok(name, r, a):
    """Source-specific admission rule -> None if admitted, else the drop reason."""
    if name == "kodcode":
        if (r.get("subset") or "").replace(" ", "_") not in a.kod_subsets: return "subset_excluded"
        if (r.get("gpt_pass_percentage") or 0) < a.kod_min_pass: return "low_pass_rate"
        if (r.get("benchmark_similarity") or 0) >= 0.8: return "benchmark_similar"
    if name == "rstar_seed" and not (r.get("verified") and r.get("is_passed")): return "not_verified"
    return None


def build(name, rows, count, a, locked, specials, cap=None):
    pidx, psize, sol13 = locked or (None, None, None)
    rep = {"read": 0, "kept": 0, "dropped": {}, "tokens": 0, "lang_kept": {}}
    kept, seen = [], set()
    def drop(why): rep["dropped"][why] = rep["dropped"].get(why, 0) + 1
    for i, r in enumerate(rows):
        if cap and rep["kept"] >= cap: break
        rep["read"] += 1
        if rep["read"] % 50000 == 0: print(f"  {name}: read {rep['read']} kept {rep['kept']}", flush=True)
        why = row_ok(name, r, a)
        if why: drop(why); continue
        try: q, ans, lang, label, key, extra = to_qa(name, r)
        except (KeyError, TypeError): drop("missing_field"); continue
        if not isinstance(q, str) or not isinstance(ans, str) or not q.strip() or not ans.strip(): drop("empty"); continue
        q, ans = q.strip(), ans.strip()
        if any(x in q or x in ans for x in specials): drop("contains_special_token_string"); continue
        if SEP in q or SEP in ans: drop("contains_qa_separator"); continue
        nq, na = count(q), count(ans)
        if nq + na + 16 > a.max_tokens: drop("too_long"); continue
        k = hashlib.sha256(re.sub(r"\s+", " ", q).lower().encode()).hexdigest()
        if k in seen: drop("duplicate_prompt"); continue
        if not A.python_blocks_parse(ans): drop("python_syntax"); continue
        if pidx is not None:
            cnt = {}
            for g in P.grams(q, 8):
                for tid in pidx.get(g, ()): cnt[tid] = cnt.get(tid, 0) + 1
            if any(c / psize[tid] >= 0.2 for tid, c in cnt.items()): drop("locked_prompt_overlap"); continue
            if sol13 and P.grams(ans, 13) & sol13.keys(): drop("locked_solution_overlap"); continue
        seen.add(k)
        kept.append({"text": f"Question: {q}{SEP}{ans}", "prov": {"seed_id": f"{name}:{key if key is not None else i}", "variant": "direct"},
                     "meta": {"source_dataset": name, "language": lang, "label": label, "prompt_tokens": nq, "answer_tokens": na, **extra}})
        rep["kept"] += 1; rep["tokens"] += nq + na; rep["lang_kept"][lang] = rep["lang_kept"].get(lang, 0) + 1
    return kept, rep


def load_locked(path):
    return locked_from_tasks(json.loads(l) for l in open(os.path.expanduser(path), encoding="utf-8") if l.strip())


def overlap_reason(prompt, answer, locked):
    """Shared locked-task rule (also used by gold_set_check): prompt shares >=20% of a locked prompt's 8-grams, or the answer shares a distinctive 13-gram of a locked reference."""
    if not locked: return None
    pidx, psize, sol13 = locked
    cnt = {}
    for g in P.grams(prompt, 8):
        for tid in pidx.get(g, ()): cnt[tid] = cnt.get(tid, 0) + 1
    if any(c / psize[tid] >= 0.2 for tid, c in cnt.items()): return "locked_prompt_overlap"
    if sol13 and P.grams(answer, 13) & sol13.keys(): return "locked_solution_overlap"
    return None


def locked_from_tasks(tasks):
    pidx, psize, m13 = {}, {}, {}
    for i, t in enumerate(tasks):
        tid = str(t.get("id", i)); gs = P.grams(t.get("prompt") or "", 8)
        if len(gs) >= 20:
            psize[tid] = len(gs)
            for g in gs: pidx.setdefault(g, set()).add(tid)
        ref = t.get("reference") or ""
        if len(ref.split()) >= 60:
            for g in P.grams(ref, 13): m13.setdefault(g, set()).add(tid)
    return pidx, psize, {g: v for g, v in m13.items() if len(v) <= 3}


FILE_RULES = {   # name -> (path must contain, path must not contain)
    "kodcode": ("", ("caution",)), "opc_edu": ("educational_instruct", ()), "rstar_seed": ("seed_sft", ()),
    "gretel": ("", ("test",)), "opc_mceval": ("mceval_instruct", ())}
COLUMNS = {"kodcode": ["question_id", "subset", "question", "solution", "gpt_pass_percentage", "benchmark_similarity"],
           "opc_edu": ["seq_id", "instruction", "code"], "rstar_seed": ["question_id", "question", "code", "verified", "is_passed"],
           "gretel": ["id", "sql_context", "sql_prompt", "sql"], "opc_mceval": ["instruction", "output"]}


def pick_files(names, must, must_not):
    """Parquet paths of one source from a repo file listing."""
    return sorted(n for n in names if n.endswith(".parquet") and must in n and not any(x in n for x in must_not))


def iter_parquet(path, columns, batch_size=2000):
    """Rows as dicts, reading only `columns` in small batches (memory stays flat, heavy unused columns are never read)."""
    import pyarrow.parquet as pq
    for batch in pq.ParquetFile(path).iter_batches(columns=columns, batch_size=batch_size):
        cols = batch.to_pydict()
        for i in range(batch.num_rows):
            yield {c: cols[c][i] for c in columns}


LC_COLUMNS = ["task_id", "difficulty", "problem_description", "starter_code", "estimated_date", "completion", "response"]


def iter_leetcode(name):
    """newfacade/LeetCodeDataset TRAIN split only (the test split is the source of 184 locked eval tasks and is never read here)."""
    from datasets import load_dataset
    ds = load_dataset("newfacade/LeetCodeDataset", split="train")
    print(name, "train rows:", len(ds), flush=True)
    for r in ds: yield {c: r.get(c) for c in LC_COLUMNS}


def iter_source(name, a):
    if name in ("leetcode", "leetcode_resp"): yield from iter_leetcode(name); return
    from huggingface_hub import HfApi, hf_hub_download
    repo = P.SOURCES[name][0]
    must, must_not = FILE_RULES[name]
    files = pick_files(HfApi().list_repo_files(repo, repo_type="dataset"), must, must_not)
    if not files: raise SystemExit(f"{name}: no parquet files matched in {repo}")
    print(name, "parquet files:", len(files), files[:3], flush=True)
    if a.max_files: files = files[:a.max_files]; print(name, "using first", len(files), "files", flush=True)
    for fn in files:
        yield from iter_parquet(hf_hub_download(repo, fn, repo_type="dataset"), COLUMNS[name])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", required=True); ap.add_argument("--tokenizer"); ap.add_argument("--locked")
    ap.add_argument("--out", required=True); ap.add_argument("--report", required=True); ap.add_argument("--max-tokens", type=int, default=1900)
    ap.add_argument("--cap", action="append", default=[], help="NAME=ROWS, repeatable"); ap.add_argument("--kod-subsets", default=",".join(KOD_DEFAULT))
    ap.add_argument("--kod-min-pass", type=float, default=0.3)
    ap.add_argument("--max-files", type=int, default=0, help="read only the first N parquet files of each source (0 = all)")
    ap.add_argument("--append", action="store_true", help="append to --out and merge into an existing --report (use to add sources without redoing finished ones)")
    a = ap.parse_args(); a.kod_subsets = {s.strip() for s in a.kod_subsets.split(",") if s.strip()}
    caps = {c.split("=")[0]: int(c.split("=")[1]) for c in a.cap}
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); count = lambda s: len(tk.encode(s).ids); specials = A.special_strings(os.path.expanduser(a.tokenizer))
    else:
        print("NOTE: no --tokenizer: tokens estimated as chars/3."); count = lambda s: len(s) // 3 + 1; specials = A.DEFAULT_SPECIALS
    locked = load_locked(a.locked) if a.locked else None
    if not locked: print("NOTE: no --locked: overlap with the locked tasks NOT checked. Do not train on this file.")
    os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(a.out))), exist_ok=True)
    old = json.load(open(os.path.expanduser(a.report))) if a.append and os.path.exists(os.path.expanduser(a.report)) else {}
    rep = {"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "locked_checked": bool(locked), "max_tokens": a.max_tokens, "sources": dict(old.get("sources", {}))}
    total = 0
    with open(os.path.expanduser(a.out), "a" if a.append else "w", encoding="utf-8") as f:
        for name in [s.strip() for s in a.sources.split(",") if s.strip()]:
            t0 = time.time()
            try:
                kept, r = build(name, iter_source(name, a), count, a, locked, specials, caps.get(name))
                for k in kept: f.write(json.dumps(k, ensure_ascii=False) + "\n")
                f.flush(); os.fsync(f.fileno())          # a killed run must not lose rows of a source the report already lists
                total += r["tokens"]
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt): raise
                r = {"error": f"{type(e).__name__}: ...{str(e)[-500:]}"}
            r["seconds"] = round(time.time() - t0, 1); rep["sources"][name] = r; print(name, json.dumps(r), flush=True)
    rep["tokens_total"] = sum(v.get("tokens", 0) for v in rep["sources"].values())
    json.dump(rep, open(os.path.expanduser(a.report), "w"), indent=1); print("saved", a.out, "tokens", total)


if __name__ == "__main__":
    main()
