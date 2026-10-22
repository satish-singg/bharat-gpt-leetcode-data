#!/usr/bin/env python3
"""Add the four FIM special tokens to an existing tokenizer.json (ids appended after the current vocabulary) and verify the result. Needs the `tokenizers` library.

  env -u PYTHONPATH ~/pilot-venv2/bin/python tools/add_fim_tokens.py --in ~/cs-data/cs-v5/tok/tokenizer.json --out ~/cs-data/cs-v6/tok/tokenizer.json

Use this when the 32k tokenizer is KEPT for the 730M. If the tokenizer is retrained instead, put the four tokens in the trainer's special-token list so they get ids 8-11
(see docs/FIM_DECISION.md). Existing ids never change, so cs-v5 shards stay valid for all non-FIM content. The model's vocab_size must then be >= the new vocabulary size.
Checks: new ids are consecutive, each token encodes to exactly one id and decodes back, a code sample round-trips, old ids unchanged."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fim import FIM_TOKENS


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from tokenizers import Tokenizer, AddedToken
    tk = Tokenizer.from_file(os.path.expanduser(a.inp)); before = tk.get_vocab_size()
    probe = "def f(x):\n    return x + 1\n\n# done"
    ids_before = tk.encode(probe).ids
    missing = [t for t in FIM_TOKENS if tk.token_to_id(t) is None]
    if not missing: sys.exit("tokenizer already has all FIM tokens")
    tk.add_special_tokens([AddedToken(t, special=True, normalized=False) for t in missing])
    ids = {t: tk.token_to_id(t) for t in FIM_TOKENS}
    assert sorted(ids[t] for t in missing) == list(range(before, before + len(missing))), ids
    for t in FIM_TOKENS:
        e = tk.encode(t).ids
        assert e == [ids[t]], (t, e)
    assert tk.encode(probe).ids == ids_before, "ordinary encoding changed"
    assert tk.decode(tk.encode(probe).ids) == probe
    os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(a.out))), exist_ok=True); tk.save(os.path.expanduser(a.out))
    print("old vocab", before, "new vocab", tk.get_vocab_size(), "ids", ids, "\nsaved", a.out, "\nSet model vocab_size >=", tk.get_vocab_size(), "(pad to a multiple of 64 if you like) and update tokenizer.yaml/prep_data.py as in docs/FIM_DECISION.md")


if __name__ == "__main__":
    main()
