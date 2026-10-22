#!/usr/bin/env python3
"""Convert downloaded Hugging Face distillation sets into ONE clean SFT file with full accounting. CPU only, read-only on inputs.

  python3 tools/hf_sft_adapter.py --hf-dir ~/hf_sft --out ~/hf_sft_clean/sft_hf.jsonl --report ~/hf_sft_clean/report.json \
      --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json [--locked locked_eval_1365.jsonl] [--max-tokens 1900]

Sources (layouts checked on the real files, 2026-10-20): CodeFeedback-Filtered-Instruction (query/answer/lang/resource),
qwen3-coder-480b-distill-mini (Input/code_output), distill_r1_code_evol_instruct (evolved_instruction + r1 response: FINAL ANSWER only,
the <think> block is dropped), fable-code-distill/fable_master.jsonl (instruction/response), self-distill qwen3-30b evol-codealpaca (instruction/output).
Filters, each counted per source: empty, contains_qa_separator (a literal \\n\\nAnswer:\\n in the text), contains_special_token_string (a literal <unk> or <eos> in text would become a special id), too_long (prompt+answer tokens + 16 > --max-tokens; NEVER truncated), duplicate instruction,
python_syntax (a ```python block that does not parse; nothing is executed), locked_overlap (verbatim 13-gram with a locked eval task).
Output row: {"text": "Question: <Q>\\n\\nAnswer:\\n<A>", "prov": {"seed_id", "variant": "direct"}, "meta": {...provenance, label "unverified_distill"}}
(the text format of phase0/sft/sft_data.py). "unverified_distill" means NOT run against tests: it ranks below test_verified and gold_checked.
"""
import argparse, ast, hashlib, io, json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "eval_framework" / "exec_track"), str(HERE.parent / "eval_framework")]

LICENSE = {"codefeedback": "Apache-2.0 (card)", "qwen3coder480b": "Apache-2.0 (card)", "fable": "Apache-2.0 (card)",
           "r1evol": "not stated", "selfdistill_evol": "not stated"}
FENCE = re.compile(r"```([a-zA-Z0-9+#_-]*)\n(.*?)```", re.S)
LANG_ALIAS = {"py": "python", "python3": "python", "js": "javascript", "node": "javascript", "c++": "cpp", "cxx": "cpp", "c#": "csharp", "ts": "typescript",
              "sh": "shell", "bash": "shell", "golang": "go", "rs": "rust", "kt": "kotlin"}


def norm_lang(x):
    x = (x or "").strip().lower()
    return LANG_ALIAS.get(x, x) or "unknown"


def _jsonl(path):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                yield i, json.loads(line)


def _parquet(path):
    import pyarrow.parquet as pq
    i = 0
    for b in pq.ParquetFile(path).iter_batches(batch_size=512):
        for r in b.to_pylist():
            yield i, r; i += 1


def final_answer(resp):
    """R1-style response: keep only what follows </think>. None if there is no closed think block."""
    if "</think>" not in resp:
        return None
    return resp.split("</think>", 1)[1].strip()


def load_sources(hf):
    hf = pathlib.Path(hf)
    p = hf / "CodeFeedback-Filtered-Instruction" / "CodeFeedback-Filtered-Instruction.jsonl"
    if p.exists():
        for i, r in _jsonl(p): yield "codefeedback", i, r.get("query"), r.get("answer"), norm_lang(r.get("lang")), r.get("resource")
    p = hf / "qwen3-coder-480b-distill-mini" / "code_distill_all.cleaned.jsonl"
    if p.exists():
        for i, r in _jsonl(p): yield "qwen3coder480b", i, r.get("Input"), r.get("code_output"), "unknown", r.get("_qid")
    p = hf / "distill_r1_code_evol_instruct" / "data" / "train-00000-of-00001.parquet"
    if p.exists():
        for i, r in _parquet(p): yield "r1evol", i, r.get("evolved_instruction"), final_answer(r.get("r1_distill_70b_response") or ""), "unknown", r.get("source")
    p = hf / "fable-code-distill" / "fable_master.jsonl"
    if p.exists():
        for i, r in _jsonl(p): yield "fable", i, r.get("instruction"), r.get("response"), "unknown", None
    p = hf / "self-distill__qwen-qwen3-30b-a3b__theblackcat102-evol-codealpaca-v1__greedy__seed-42" / "data" / "train-00000-of-00001.parquet"
    if p.exists():
        for i, r in _parquet(p):
            if r.get("status") == "success": yield "selfdistill_evol", i, r.get("instruction"), r.get("output"), "unknown", r.get("source_dataset")


def python_blocks_parse(answer):
    for lang, code in FENCE.findall(answer):
        if norm_lang(lang) == "python":
            try: ast.parse(code)
            except (SyntaxError, ValueError, MemoryError, RecursionError): return False
    return True


def infer_lang(lang, answer):
    if lang not in ("unknown", ""): return lang
    m = FENCE.search(answer)
    return norm_lang(m.group(1)) if m and m.group(1) else "unknown"


DEFAULT_SPECIALS = ("<pad>", "<unk>", "<bos>", "<eos>", "<s>", "</s>", "<|endoftext|>")


def special_strings(tokenizer_json):
    """Content of every added/special token in a tokenizer.json (a literal copy in text would be encoded as the special id)."""
    try:
        return tuple(t["content"] for t in json.load(open(tokenizer_json, encoding="utf-8")).get("added_tokens", []) if t.get("content"))
    except Exception:
        return DEFAULT_SPECIALS


def build(rows, count_tokens, max_tokens=1900, overhead=16, locked_idx=None, grams=None, specials=DEFAULT_SPECIALS):
    """rows: iterable of (source, idx, question, answer, lang, upstream). -> (kept list, report dict)."""
    rep, kept, seen = {}, [], set()
    def r(src): return rep.setdefault(src, {"read": 0, "kept": 0, "dropped": {}, "lang_kept": {}})
    for src, idx, q, a, lang, up in rows:
        s = r(src); s["read"] += 1
        def drop(why): s["dropped"][why] = s["dropped"].get(why, 0) + 1
        if not isinstance(q, str) or not isinstance(a, str) or not q.strip() or not a.strip(): drop("empty"); continue
        q, a = q.strip(), a.strip()
        if any(x in q or x in a for x in specials): drop("contains_special_token_string"); continue   # would be encoded as a special id (e.g. <unk>)
        if "\n\nAnswer:\n" in q or "\n\nAnswer:\n" in a: drop("contains_qa_separator"); continue   # would move the loss-mask boundary in sft_data.py
        nq, na = count_tokens(q), count_tokens(a)
        if nq + na + overhead > max_tokens: drop("too_long"); continue
        key = hashlib.sha256(re.sub(r"\s+", " ", q).lower().encode()).hexdigest()
        if key in seen: drop("duplicate_instruction"); continue
        if not python_blocks_parse(a): drop("python_syntax"); continue
        if locked_idx and any(g in locked_idx for g in grams(q + "\n" + a)): drop("locked_overlap"); continue
        seen.add(key)
        lg = infer_lang(lang, a)
        sid = f"{src}:{idx}"
        kept.append({"text": f"Question: {q}\n\nAnswer:\n{a}", "prov": {"seed_id": sid, "variant": "direct"},
                     "meta": {"source_dataset": src, "source_row_id": idx, "language": lg, "upstream": up, "dataset_license": LICENSE.get(src, "unrecorded"),
                              "prompt_tokens": nq, "answer_tokens": na, "label": "unverified_distill", "python_syntax_checked": True}})
        s["kept"] += 1; s["lang_kept"][lg] = s["lang_kept"].get(lg, 0) + 1
    return kept, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hf-dir", required=True); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
    ap.add_argument("--tokenizer"); ap.add_argument("--locked"); ap.add_argument("--max-tokens", type=int, default=1900)
    a = ap.parse_args()
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(a.tokenizer); count = lambda s: len(tk.encode(s).ids)
    else:
        print("NOTE: no --tokenizer: token counts are estimated as chars/3 (conservative)."); count = lambda s: len(s) // 3 + 1
    idx = grams = None
    if a.locked:
        import overlap as O
        locked = [json.loads(l) for l in open(a.locked, encoding="utf-8") if l.strip()]
        idx, grams = O.fingerprints(locked)[0], O._grams
    kept, rep = build(load_sources(a.hf_dir), count, a.max_tokens, locked_idx=idx, grams=grams,
                      specials=special_strings(a.tokenizer) if a.tokenizer else DEFAULT_SPECIALS)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for k in kept: f.write(json.dumps(k, ensure_ascii=False) + "\n")
    toks = sorted(k["meta"]["prompt_tokens"] + k["meta"]["answer_tokens"] for k in kept)
    out = {"kept": len(kept), "tokens_total": sum(toks), "tokens_p50_p90_max": [toks[len(toks) // 2], toks[int(len(toks) * .9)], toks[-1]] if toks else None,
           "max_tokens": a.max_tokens, "locked_checked": bool(a.locked), "tokenizer": a.tokenizer or "estimate chars/3", "per_source": rep}
    json.dump(out, open(a.report, "w"), indent=1); print(json.dumps(out, indent=1))
    if not a.locked: print("\nNOTE: --locked not given: overlap with the 1,365 locked eval tasks was NOT checked. Do not train on this file yet.")


if __name__ == "__main__":
    main()
