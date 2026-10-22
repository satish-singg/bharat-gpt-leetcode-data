#!/usr/bin/env python3
"""Measure candidate SFT / RL sets before any use: size, token length, parse rate, trust-relevant flags and overlap with the locked eval tasks.
CPU only, streams N rows per source (shuffled, seed 0), writes nothing but the report.

  env -u PYTHONPATH ~/pilot-venv2/bin/python -u tools/sft_pilot.py --sources kodcode,opc_edu,gretel --limit 5000 \
      --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --locked LOCKED.jsonl --out ~/sft_pilot.json

--locked is a jsonl of locked tasks ({"id","prompt","reference"?}); overlap is checked two ways on prompt+solution, ignoring word sequences that occur in more than 3 locked tasks (boilerplate):
  exact13 / loose8 = any shared 13- / 8-word gram over prompt+solution (NOISY: punctuation is stripped, so code idioms and input-format sentences match; use only to read the examples).
prompt_contained = the row's PROMPT shares >=20% of a locked task's prompt 8-grams (the meaningful problem-level number; locked prompts under 20 grams are not indexed).
Both are LOWER bounds for paraphrased tasks (e.g. KodCode rewrites LeetCode): a clean result is not proof of no leakage.
Trust labels: nothing here is test_verified. Tests written by the same model as the solution are NOT independent evidence."""
import argparse, ast, json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "eval_framework", "exec_track"), os.path.join(HERE, "..", "eval_framework")]

FENCE = re.compile(r"```([a-zA-Z0-9+#_-]*)\n(.*?)```", re.S)
THINK = re.compile(r"<think>.*?</think>", re.S)


def _fence_lang(text):
    m = FENCE.search(text or "")
    return (m.group(1).lower() or "unknown") if m else "unknown"


# name -> (repo, config, split, adapter). Adapter(row) -> dict(prompt, solution, tests, lang, extra{})
def _kod(r):
    return dict(prompt=r.get("question"), solution=r.get("solution"), tests=r.get("test"), lang="python",
                extra={"subset": r.get("subset"), "sim_ge_0.8": (r.get("benchmark_similarity") or 0) >= 0.8, "pass_pct_ge_0.5": (r.get("gpt_pass_percentage") or 0) >= 0.5,
                       "filtered": bool(r.get("filter_reason"))})

def _rstar_seed(r):
    return dict(prompt=r.get("question"), solution=r.get("code"), tests=None, lang="python",
                extra={"verified": bool(r.get("verified")), "is_passed": bool(r.get("is_passed"))})

def _rstar_syn(r):
    return dict(prompt=r.get("question"), solution=r.get("code"), tests=None, lang="python", extra={"seed_source": r.get("seed_source")})

def _openr1(r):
    return dict(prompt=r.get("problem_statement"), solution=r.get("gold_standard_solution"), tests=str(r.get("verification_info")), lang="python", extra={"source": r.get("source")})

def _prime(r):
    return dict(prompt=r.get("prompt"), solution=r.get("gold_standard_solution"), tests=r.get("verification_info"), lang="python", extra={"source": r.get("source")})

def _opc_edu(r):
    return dict(prompt=r.get("instruction"), solution=r.get("code"), tests="\n".join(r.get("testcase") or []), lang="python", extra={"has_tests": bool(r.get("testcase"))})

def _opc_mc(r):
    return dict(prompt=r.get("instruction"), solution=r.get("output"), tests=None, lang=_fence_lang(r.get("output")), extra={})

def _gretel(r):
    return dict(prompt=(r.get("sql_context") or "") + "\n" + (r.get("sql_prompt") or ""), solution=r.get("sql"), tests=None, lang="sql",
                extra={"complexity": r.get("sql_complexity")})

def _pipable(r):
    return dict(prompt=(r.get("schema") or "") + "\n" + (r.get("question") or ""), solution=r.get("query"), tests=None, lang="sql", extra={})

def _sqlcc(r):
    return dict(prompt=(r.get("context") or "") + "\n" + (r.get("question") or ""), solution=r.get("answer"), tests=None, lang="sql", extra={})

def _opus(r):
    a = r.get("assistant") or ""
    return dict(prompt=r.get("user"), solution=THINK.sub("", a).strip(), tests=None, lang=_fence_lang(a),
                extra={"has_think": "<think>" in a, "has_code_fence": "```" in a})

SOURCES = {
    "kodcode": ("KodCode/KodCode-V1", None, "train", _kod),
    "rstar_seed": ("microsoft/rStar-Coder", "seed_sft", "train", _rstar_seed),
    "rstar_syn": ("microsoft/rStar-Coder", "synthetic_sft", "train", _rstar_syn),
    "openr1": ("open-r1/verifiable-coding-problems-python", None, "train", _openr1),
    "prime": ("PrimeIntellect/verifiable-coding-problems", None, "train", _prime),
    "opc_edu": ("OpenCoder-LLM/opc-sft-stage2", "educational_instruct", "train", _opc_edu),
    "opc_mceval": ("OpenCoder-LLM/opc-sft-stage2", "mceval_instruct", "train", _opc_mc),
    "gretel": ("gretelai/synthetic_text_to_sql", None, "train", _gretel),
    "pipable": ("PipableAI/pip-txt-to-sql-spider-bird-dataset", None, "train", _pipable),
    "sqlcc": ("b-mc2/sql-create-context", None, "train", _sqlcc),
    "opus_reason": ("sasindumalhara/claude_opus-4.6_4.7_coding_reasoning", None, "train", _opus),
}


def grams(text, n):
    w = re.sub(r"[^a-z0-9_]+", " ", (text or "").lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def analyze(items, count, limit, max_tokens, locked13=None, locked8=None, n_examples=4, pidx=None, psize=None, thr=0.2):
    """items: iterable of adapter dicts. Returns a report dict."""
    n = ok_py = py_total = too_long = empty = dup = 0
    toks, langs, seen, extras = [], {}, set(), {}
    hit13 = hit8 = hitp = 0
    by_sub, examples, tasks_hit, by_prompt = {}, [], {}, {}
    for it in items:
        if n >= limit: break
        p, s = it.get("prompt"), it.get("solution")
        if not isinstance(p, str) or not isinstance(s, str) or not p.strip() or not s.strip():
            empty += 1; continue
        n += 1
        k = re.sub(r"\s+", " ", p).strip().lower()
        if k in seen: dup += 1
        seen.add(k)
        t = count(p) + count(s)
        toks.append(t); too_long += t + 16 > max_tokens
        langs[it["lang"]] = langs.get(it["lang"], 0) + 1
        if it["lang"] == "python":
            py_total += 1
            code = "\n".join(c for _, c in FENCE.findall(s)) or s
            try: ast.parse(code); ok_py += 1
            except (SyntaxError, ValueError, MemoryError, RecursionError): pass
        for key, v in (it.get("extra") or {}).items():
            d = extras.setdefault(key, {})
            if isinstance(v, bool): d["true"] = d.get("true", 0) + int(v)
            else: d[str(v)] = d.get(str(v), 0) + 1
        if locked13 is not None:
            g13 = grams(p + "\n" + s, 13) & locked13.keys(); g8 = grams(p + "\n" + s, 8) & locked8.keys()
            hit13 += bool(g13); hit8 += bool(g8)
            sub = str((it.get("extra") or {}).get("subset") or (it.get("extra") or {}).get("source") or (it.get("extra") or {}).get("seed_source") or "-")
            c = by_sub.setdefault(sub, [0, 0, 0]); c[0] += 1; c[1] += bool(g13); c[2] += bool(g8)
            if pidx is not None:
                cnt = {}
                for g in grams(p, 8):
                    for tid in pidx.get(g, ()): cnt[tid] = cnt.get(tid, 0) + 1
                ph = [tid for tid, c in cnt.items() if c / psize[tid] >= thr]
                hitp += bool(ph)
                if ph: by_prompt[sub] = by_prompt.get(sub, 0) + 1
            row_tids = set()
            for g in g13 or g8:
                row_tids |= set(locked13.get(g) or locked8.get(g) or ())
            for tid in row_tids:
                tasks_hit[tid] = tasks_hit.get(tid, 0) + 1         # once per row and task, not once per shared gram
            if (g13 or g8) and len(examples) < n_examples:
                g = sorted(g13 or g8)[0]; examples.append({"shared_words": g, "prompt_head": p.strip()[:160], "locked_ids": sorted(locked13.get(g) or locked8.get(g) or [])[:3]})
    toks.sort()
    q = lambda f: toks[min(len(toks) - 1, int(len(toks) * f))] if toks else None
    rep = {"rows": n, "empty_or_missing": empty, "dup_prompts": dup, "tokens_total": sum(toks), "tokens_mean": round(sum(toks) / n, 1) if n else None,
           "tokens_p50_p90_max": [q(.5), q(.9), toks[-1] if toks else None], "too_long_rate": round(too_long / n, 4) if n else None,
           "languages": dict(sorted(langs.items(), key=lambda x: -x[1])[:8]), "extras": extras}
    if py_total: rep["python_parse_rate"] = round(ok_py / py_total, 4)
    if locked13 is not None:
        rep["overlap_by_subset[rows,exact13,loose8]"] = dict(sorted(by_sub.items(), key=lambda x: -x[1][0])[:12])
        if pidx is not None:
            rep["prompt_contained_rate"] = round(hitp / n, 5) if n else None; rep["prompt_contained_by_subset"] = dict(sorted(by_prompt.items(), key=lambda x: -x[1])[:12])
        rep["locked_tasks_hit"] = len(tasks_hit); rep["top_locked_tasks_hit"] = dict(sorted(tasks_hit.items(), key=lambda x: -x[1])[:8]); rep["overlap_examples"] = examples
    if locked13 is not None: rep["locked_overlap_exact13"] = round(hit13 / n, 5) if n else None; rep["locked_overlap_loose8"] = round(hit8 / n, 5) if n else None
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", required=True, help="comma list of: " + ",".join(SOURCES)); ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--tokenizer"); ap.add_argument("--locked"); ap.add_argument("--max-tokens", type=int, default=1900); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); count = lambda s: len(tk.encode(s).ids)
    else:
        print("NOTE: no --tokenizer: tokens estimated as chars/3."); count = lambda s: len(s) // 3 + 1
    l13 = l8 = pidx = psize = None
    if a.locked:
        m13, m8 = {}, {}
        for i, line in enumerate(open(os.path.expanduser(a.locked), encoding="utf-8")):
            if line.strip():
                t = json.loads(line); tid = str(t.get("id", i)); txt = (t.get("prompt") or "") + "\n" + (t.get("reference") or "")
                for g in grams(txt, 13): m13.setdefault(g, set()).add(tid)
                for g in grams(txt, 8): m8.setdefault(g, set()).add(tid)
        # a gram that occurs in more than 3 locked tasks is boilerplate (e.g. an input-format sentence): it proves nothing about leakage
        pidx, psize = {}, {}
        for i, line in enumerate(open(os.path.expanduser(a.locked), encoding="utf-8")):
            if line.strip():
                t = json.loads(line); tid = str(t.get("id", i)); gs = grams(t.get("prompt") or "", 8)
                if len(gs) >= 20:
                    psize[tid] = len(gs)
                    for g in gs: pidx.setdefault(g, set()).add(tid)
        print("locked prompts indexed for containment:", len(psize))
        l13 = {g: v for g, v in m13.items() if len(v) <= 3}; l8 = {g: v for g, v in m8.items() if len(v) <= 3}
        print("locked grams kept (distinctive):", len(l13), "of", len(m13), "|", len(l8), "of", len(m8))
    else:
        print("NOTE: no --locked: overlap with the locked eval tasks NOT checked.")
    from datasets import load_dataset
    rep = {"limit": a.limit, "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "locked_checked": bool(a.locked)}
    for name in [s.strip() for s in a.sources.split(",") if s.strip()]:
        t0 = time.time()
        try:
            repo, cfg, split, ad = SOURCES[name]
            ds = load_dataset(repo, **({"name": cfg} if cfg else {}), split=split, streaming=True).shuffle(seed=0, buffer_size=2000)
            rep[name] = analyze((ad(r) for r in ds), count, a.limit, a.max_tokens, l13, l8, pidx=pidx, psize=psize)
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt): raise
            rep[name] = {"error": f"{type(e).__name__}: ...{str(e)[-500:]}"}
        rep[name]["seconds"] = round(time.time() - t0, 1)
        print(name, json.dumps(rep[name], indent=1), flush=True)
    json.dump(rep, open(os.path.expanduser(a.out), "w"), indent=1); print("saved", a.out)


if __name__ == "__main__":
    main()
