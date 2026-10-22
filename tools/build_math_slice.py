#!/usr/bin/env python3
"""Select a math slice (the 5-7% problem-solving math share of the 730M mix; first written for a 124M ablation that was dropped, see docs/MATH_AND_FIM_DECISIONS.md). CPU only; reads FineMath-4plus parquet files directly (column-projected, spread evenly over the
whole dataset so the sample is NOT the head of the first file), filters junk, optionally favours CS-flavoured math, counts tokens with OUR tokenizer, writes jsonl.

  env -u PYTHONPATH ~/pilot-venv2/bin/python -u tools/build_math_slice.py --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json \
      --locked ~/locked_eval_1365.jsonl --out ~/math_slice/math_train.jsonl --heldout-out ~/math_slice/math_heldout.jsonl --target-tokens 200000000

Filters (each counted): empty/short, too long (> --max-tokens), mojibake (U+FFFD or 'Ã'/'â€' runs), meta-refresh/redirect pages, number-fact pages ("Is 12345 a prime number?"),
non-English-looking (ASCII letter share < 0.6 of letters), locked overlap (doc shares >= 20% of a locked task's prompt 8-grams), and with --focus cs: keyword density below --min-density
(hits of discrete-math / algorithm words per 1,000 characters). The --focus cs choice follows the finding that structured derivations, not generic school math, are what interacts with code.
A held-out slice (--heldout-tokens, default 2M) is taken from the same stream (every k-th accepted document, so it spans the same files as the train slice) and never goes into the train file: use it to measure math loss of both ablation arms."""
import argparse, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

KEYWORDS = ("algorithm", "complexity", "recurrence", "induction", "combinator", "permutation", "binomial", "graph", "vertex", "vertices", "edge", "tree", "modular", "modulo", "congruen",
            "gcd", "greatest common divisor", "prime", "divisib", "binary", "bit", "matrix", "determinant", "probability", "expected value", "expectation", "pigeonhole", "counting",
            "lemma", "theorem", "proof", "sequence", "series", "summation", "logarithm", "exponential", "floor", "ceiling", "set", "function", "relation", "boolean", "logic")
MOJI = re.compile(r"(�|Ã.|â€)")
REFRESH = re.compile(r"http-equiv=[\"']?refresh|window\.location|<meta ", re.I)
NUMBER_FACT = re.compile(r"^\s*(is|are|what (is|are)|properties of|factors of|divisors of)\s+(the\s+)?(number\s+)?[\d,\.]{4,}", re.I)


def reject_reason(text, max_chars, min_chars=400):
    """Cheap junk filters -> reason or None."""
    if not isinstance(text, str) or len(text) < min_chars: return "short"
    if len(text) > max_chars: return "too_long"
    head = text[:300]
    if NUMBER_FACT.match(head): return "number_fact_page"
    if REFRESH.search(text[:2000]): return "redirect_page"
    if len(MOJI.findall(text)) >= 3: return "mojibake"
    letters = [c for c in text[:3000] if c.isalpha()]
    if letters and sum(c.isascii() for c in letters) / len(letters) < 0.6: return "not_english"
    return None


def keyword_density(text):
    t = text.lower()
    return sum(t.count(k) for k in KEYWORDS) / (len(t) / 1000.0)


def spread(files, n):
    """n files evenly spaced over the sorted list (the head of the first file is not the dataset)."""
    if n <= 0 or n >= len(files): return list(files)
    return [files[int(i * len(files) / n)] for i in range(n)]


def select(docs, count, target, heldout_target, focus, min_density, max_tokens, locked=None, grams=None, progress=0):
    """docs: iterable of text. Yields ('train'|'heldout', text, ntokens); stops when both targets are met. rep is filled with counts."""
    rep = {"scanned": 0, "dropped": {}}
    got = {"train": 0, "heldout": 0}
    out = []
    stride = max(2, round((target + heldout_target) / heldout_target)) if heldout_target > 0 else 2
    for text in docs:
        rep["scanned"] += 1
        if progress and rep["scanned"] % progress == 0: print(f"  scanned {rep['scanned']:,} accepted {len(out):,} tokens {dict(got)} dropped {rep['dropped']}", flush=True)
        why = reject_reason(text, max_chars=max_tokens * 6)
        if not why and focus == "cs" and keyword_density(text) < min_density: why = "low_keyword_density"
        if not why and locked is not None:
            pidx, psize = locked
            cnt = {}
            for g in grams(text, 8):
                for tid in pidx.get(g, ()): cnt[tid] = cnt.get(tid, 0) + 1
            if any(c / psize[tid] >= 0.2 for tid, c in cnt.items()): why = "locked_overlap"
        if why: rep["dropped"][why] = rep["dropped"].get(why, 0) + 1; continue
        n = count(text)
        if n > max_tokens: rep["dropped"]["too_long"] = rep["dropped"].get("too_long", 0) + 1; continue
        # every stride-th accepted doc goes to the held-out slice (deterministic), so held-out and train span the same files; once held-out is full everything is train
        part = "heldout" if (heldout_target > 0 and got["heldout"] < heldout_target and len(out) % stride == stride - 1) else "train"
        got[part] += n; out.append((part, text, n))
        if got["train"] >= target and got["heldout"] >= heldout_target: break
    rep["tokens"] = dict(got); rep["accepted_docs"] = len(out)
    return out, rep


NUMINA_TYPES_DEFAULT = ("Algebra", "Number Theory", "Combinatorics", "Logic and Puzzles", "Inequalities")


def numina_text(row, types, drops):
    """NuminaMath-1.5 row -> training text, or None (reason counted in drops). Only human-sourced, valid, complete rows of the wanted problem types."""
    def no(why): drops[why] = drops.get(why, 0) + 1; return None
    if row.get("synthetic"): return no("numina_synthetic")
    if str(row.get("problem_is_valid")) != "Yes" or str(row.get("solution_is_valid")) != "Yes": return no("numina_not_valid")
    if row.get("problem_type") not in types: return no("numina_type_excluded")
    p, sol = (row.get("problem") or "").strip(), (row.get("solution") or "").strip()
    if len(p) < 20 or len(sol) < 40: return no("numina_short")
    return f"Problem:\n{p}\n\nSolution:\n{sol}"


def iter_numina(types, drops, n_files=0):
    from huggingface_hub import HfApi, hf_hub_download
    repo = "AI-MO/NuminaMath-1.5"
    names = sorted(n for n in HfApi().list_repo_files(repo, repo_type="dataset") if n.endswith(".parquet"))
    use = spread(names, n_files)
    print("numina parquet files:", len(names), "using", len(use), use[:3], flush=True)
    import build_sft_corpus as B
    cols = ["problem", "solution", "problem_type", "problem_is_valid", "solution_is_valid", "synthetic"]
    for fn in use:
        for r in B.iter_parquet(hf_hub_download(repo, fn, repo_type="dataset"), cols):
            t = numina_text(r, types, drops)
            if t: yield t


def iter_finemath(n_files, columns=("text",)):
    from huggingface_hub import HfApi, hf_hub_download
    repo = "HuggingFaceTB/finemath"
    names = sorted(n for n in HfApi().list_repo_files(repo, repo_type="dataset") if n.startswith("finemath-4plus/") and n.endswith(".parquet"))
    use = spread(names, n_files)
    print("finemath-4plus parquet files:", len(names), "using", len(use), use[:3], flush=True)
    import build_sft_corpus as B
    for fn in use:
        for r in B.iter_parquet(hf_hub_download(repo, fn, repo_type="dataset"), list(columns)):
            yield r["text"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--locked"); ap.add_argument("--out", required=True); ap.add_argument("--heldout-out", required=True)
    ap.add_argument("--target-tokens", type=int, default=200_000_000); ap.add_argument("--heldout-tokens", type=int, default=2_000_000)
    ap.add_argument("--files", type=int, default=12, help="parquet files to read, evenly spread over the dataset"); ap.add_argument("--focus", choices=["cs", "none"], default="cs")
    ap.add_argument("--source", choices=["finemath4plus", "numina15"], default="finemath4plus", help="numina15: AI-MO/NuminaMath-1.5 problem+solution pairs (human-sourced, valid, chosen problem types); --focus is ignored for it")
    ap.add_argument("--numina-types", default=",".join(NUMINA_TYPES_DEFAULT))
    ap.add_argument("--min-density", type=float, default=2.0); ap.add_argument("--max-tokens", type=int, default=6000); ap.add_argument("--report")
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); count = lambda s: len(tk.encode(s).ids) + 1
    locked = None
    if a.locked:
        import build_sft_corpus as B
        pidx, psize, _ = B.load_locked(a.locked); locked = (pidx, psize)
    import sft_pilot as P
    t0 = time.time()
    pre = {}
    if a.source == "numina15":
        docs = iter_numina({x.strip() for x in a.numina_types.split(",") if x.strip()}, pre, 0)
        out, rep = select(docs, count, a.target_tokens, a.heldout_tokens, "none", 0, a.max_tokens, locked, P.grams, progress=50000)
        rep["prefilter_dropped"] = pre
    else:
        out, rep = select(iter_finemath(a.files), count, a.target_tokens, a.heldout_tokens, a.focus, a.min_density, a.max_tokens, locked, P.grams, progress=50000)
    for path, part in ((a.out, "train"), (a.heldout_out, "heldout")):
        os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(path))), exist_ok=True)
        with open(os.path.expanduser(path), "w", encoding="utf-8") as f:
            for p, text, n in out:
                if p == part: f.write(json.dumps({"text": text, "source": a.source, "tokens": n}, ensure_ascii=False) + "\n")
    rep.update({"source": a.source, "focus": a.focus, "min_density": a.min_density, "files": a.files, "target_tokens": a.target_tokens, "seconds": round(time.time() - t0, 1),
                "accept_rate": round(rep["accepted_docs"] / max(1, rep["scanned"]), 4), "reached_target": rep["tokens"]["train"] >= a.target_tokens})
    print(json.dumps(rep, indent=1))
    if a.report: json.dump(rep, open(os.path.expanduser(a.report), "w"), indent=1)
    if not rep["reached_target"]: print("WARNING: target not reached: add --files or lower --min-density (more tokens per run, weaker focus).")


if __name__ == "__main__":
    main()
