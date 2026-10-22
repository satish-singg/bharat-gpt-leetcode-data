#!/usr/bin/env python3
"""Train a CANDIDATE tokenizer for the 730M model and write it next to the study tools; it never replaces cs-v5/tok.
Recipe = the cs-v5 recipe (byte-level BPE, 32,000 entries, min_frequency 2) with two changes:
  1. every digit is its own token (Digits(individual_digits=True) before ByteLevel). The cs-v5 tokenizer merges digit runs: "1234567" -> "Ġ1234" + "567".
  2. the four FIM tokens are special tokens 8..11 (ids 0..7 stay exactly as in cs-v5), then <think> </think> = 12, 13 and two spare = 14, 15; vocab_size stays 32,000 (a multiple of 128).
Train on text that is NOT in the study samples (use a different --seed for sample_by_source, and --skip for files you also study):

  python3 tools/train_candidate_tokenizer.py --out-dir ~/tok_cand --max-doc-chars 20000 \\
      --text ~/tok_train_samples/code_python.jsonl --text ~/tok_train_samples/code_java_sql_js.jsonl --text ~/math/numina.jsonl:2000 ...
Each --text is PATH, PATH:SKIP, PATH:SKIP:LIMIT or PATH:SKIP:LIMIT:CHARS (skip the first SKIP lines, e.g. the ones tools/tokenizer_study.py already measured; read at most LIMIT lines after that; stop once CHARS characters of text were used - gives every file the same volume, 0 = no limit). Needs the `tokenizers` library."""
import argparse, json, os, sys

SPECIALS = ["<pad>", "<unk>", "<bos>", "<eos>", "<|system|>", "<|user|>", "<|assistant|>", "<|end|>",
            "<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>", "<|fim_pad|>",
            "<think>", "</think>", "<|reserved_0|>", "<|reserved_1|>"]       # ids 12-13 = reasoning notes (docs/VERIFIED_DATA_PLAN.md); 14-15 spare, so no later tokenizer change is needed


def docs(specs, max_chars):
    for spec in specs:
        path, skip, limit, budget = (spec.split(":") + ["0", "0", "0"])[:4]; skip, limit, budget = int(skip or 0), int(limit or 0), int(budget or 0)
        used = 0
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < skip or not line.strip(): continue
                if limit and i >= skip + limit: break
                if budget and used >= budget: break                      # equal TEXT VOLUME per file (e.g. Python = Java), not equal document counts
                try: t = json.loads(line).get("text")
                except ValueError: continue
                if isinstance(t, str) and t: used += min(len(t), max_chars); yield t[:max_chars]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", action="append", required=True); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--vocab-size", type=int, default=32000); ap.add_argument("--max-doc-chars", type=int, default=20000)
    a = ap.parse_args()
    from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Digits(individual_digits=True), pre_tokenizers.ByteLevel(add_prefix_space=False)])
    tok.decoder = decoders.ByteLevel()
    tr = trainers.BpeTrainer(vocab_size=a.vocab_size, min_frequency=2, special_tokens=SPECIALS, initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator(docs(a.text, a.max_doc_chars), tr)
    ids = {s: tok.token_to_id(s) for s in SPECIALS}
    assert [ids[s] for s in SPECIALS] == list(range(len(SPECIALS))), f"special ids not 0..{len(SPECIALS)-1}: {ids}"
    assert tok.get_vocab_size() == a.vocab_size, tok.get_vocab_size()
    for probe in ("x = 1234567", "def f(x):\n    return x\n", "\t\tif a == b:\n", "SELECT 1;", "\u00e9\u4e2d\U0001f600"):
        assert tok.decode(tok.encode(probe).ids) == probe, probe
    os.makedirs(os.path.expanduser(a.out_dir), exist_ok=True)
    out = os.path.join(os.path.expanduser(a.out_dir), "tokenizer.json"); tok.save(out)
    print("saved", out, "vocab", tok.get_vocab_size(), "special ids", ids)
    print("1234567 ->", tok.encode("x = 1234567").tokens)


if __name__ == "__main__":
    main()
