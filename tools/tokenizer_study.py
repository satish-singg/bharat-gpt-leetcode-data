#!/usr/bin/env python3
"""Measure a tokenizer on real text so the "retrain the tokenizer for 730M?" decision rests on numbers.

CPU only, read-only. Needs `pip install tokenizers`. It never changes any tokenizer or data.

  python3 tools/tokenizer_study.py --tokenizer cs-v5/tok/tokenizer.json \
      --sample python=py.jsonl --sample cpp=cpp.jsonl --sample se=stackexchange.jsonl [--max-docs 2000]
  python3 tools/tokenizer_study.py --tokenizer A.json --compare B.json --sample ...     # side by side

Each --sample is NAME=PATH, a .jsonl file with a "text" field per line (or a plain text file, one document per blank-line block).
Report per sample: documents, bytes, tokens, bytes per token (higher = better compression), tokens per 1,000 characters,
round-trip failures, and the fraction of byte-fallback pieces. Then a fixed probe of whitespace and digit behaviour.
Comparing two tokenizers: ONLY compare tokens-per-byte across the SAME text. Never compare per-token loss across tokenizers; use bits per byte.
"""
import argparse, json, re, sys
from pathlib import Path

PROBES = ["def f(x):\n    return x", "\n    x", "\n        x", "\n\tx", "    ", "\n\n", "x = 1234567", "2024-10-20", "public static void main(String[] args) {",
          "SELECT a, b FROM t WHERE a > 3;", "fn main() {\n    println!(\"hi\");\n}", "#include <stdio.h>\nint main(void) {\n    return 0;\n}"]


def load_docs(path, max_docs):
    p = Path(path); docs = []
    if p.suffix == ".jsonl":
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: t = json.loads(line).get("text")
                except Exception: continue
                if isinstance(t, str) and t: docs.append(t)
                if len(docs) >= max_docs: break
    else:
        docs = [b for b in p.read_text(encoding="utf-8", errors="replace").split("\n\n\n") if b.strip()][:max_docs]
    return docs


def measure(tok, docs):
    n_bytes = n_chars = n_tok = bad = n_fb = 0
    for d in docs:
        enc = tok.encode(d); ids = enc.ids
        # byte fallback: <0xNN> pieces (sentencepiece style) or, for byte-level BPE, pieces that decode to a PARTIAL utf-8 sequence (U+FFFD alone)
        n_fb += sum(1 for p, i in zip(enc.tokens, ids) if re.fullmatch(r"<0x[0-9A-Fa-f]{2}>", p) or "\ufffd" in tok.decode([i]))
        n_bytes += len(d.encode("utf-8")); n_chars += len(d); n_tok += len(ids)
        if tok.decode(ids) != d: bad += 1
    return {"docs": len(docs), "bytes": n_bytes, "chars": n_chars, "tokens": n_tok,
            "bytes_per_token": round(n_bytes / max(1, n_tok), 3), "tokens_per_1k_chars": round(1000 * n_tok / max(1, n_chars), 1), "roundtrip_failures": bad,
            "byte_fallback_pieces": n_fb, "byte_fallback_share": round(n_fb / max(1, n_tok), 5)}


def probe(tok):
    out = {}
    for s in PROBES:
        enc = tok.encode(s); out[s] = list(zip(enc.tokens, enc.ids))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--compare")
    ap.add_argument("--sample", action="append", default=[], help="NAME=PATH")
    ap.add_argument("--max-docs", type=int, default=2000)
    a = ap.parse_args()
    try:
        from tokenizers import Tokenizer
    except ImportError:
        sys.exit("pip install tokenizers")
    toks = {"A": Tokenizer.from_file(a.tokenizer)}
    if a.compare: toks["B"] = Tokenizer.from_file(a.compare)
    for k, t in toks.items(): print(f"tokenizer {k}: vocab {t.get_vocab_size()}")
    for spec in a.sample:
        name, _, path = spec.partition("=")
        docs = load_docs(path, a.max_docs)
        print(f"\n[{name}] {len(docs)} documents from {path}")
        for k, t in toks.items(): print(f"  {k}: {json.dumps(measure(t, docs))}")
    print("\nwhitespace / digit / language probes (token pieces):")
    for s in PROBES:
        print(f"  {s!r}")
        for k, t in toks.items(): print(f"    {k}: {[p for p, _ in probe(t)[s]]}")
    print("\nHow to read: newline+indent probes show whether '\\n    ' is ONE token (the cs-v5 quirk). Digits show whether number runs merge.")


if __name__ == "__main__":
    main()
