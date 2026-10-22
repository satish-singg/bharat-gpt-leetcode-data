#!/usr/bin/env python3
"""Build arm B of the 124M "does math help coding" ablation: the cs-v5 packed data with ~8% of the tokens REPLACED by the math slice, total tokens unchanged
(same steps, same compute, same schedule: only the mix differs). Arm A is the original packed folder, untouched. CPU only.

  env -u PYTHONPATH ~/pilot-venv2/bin/python tools/make_math_arm.py --packed ~/cs-data/cs-v5/packed --math ~/math_slice/math_train.jsonl \
      --heldout ~/math_slice/math_heldout.jsonl --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --out ~/cs-data/cs-v5-math8/packed --fraction 0.08

How: the loader (PackedIndex) draws sequences from a seeded permutation over ALL train shards, so replacing whole shards at evenly spaced positions mixes the math in uniformly.
Replaced shards keep their file names and sizes (train_007.bin etc.); every other shard is a symlink to arm A's file; valid_* and eval_frozen_* are symlinks (both arms are
validated on the SAME data). pack_manifest.json is rewritten with the new hashes, the new dataset fingerprint (same rule as phase0_utils.dataset_fingerprint), the unchanged
tokenizer_sha256 and a "math_arm" block. The held-out math tokens go to <out>/extra_eval/math_heldout.bin (NOT matched by train_/valid_ globs, so the trainer never reads it).
Documents are cut where the shard ends (a document may be split across the shard boundary; harmless for next-token training)."""
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np

EOS_ID = 3


def sha256_file(p, chunk=1 << 24):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""): h.update(b)
    return h.hexdigest()


def fingerprint(per):
    """Same rule as phase0_utils.dataset_fingerprint: sha256 over sorted 'name:digest;'."""
    h = hashlib.sha256()
    for n in sorted(per): h.update(f"{n}:{per[n]};".encode())
    return h.hexdigest()


def choose_replaced(sizes, fraction):
    """sizes: {shard_name: tokens} for train shards. Evenly spaced shards whose total is the closest to fraction*total (never the last, possibly shorter, shard)."""
    names = sorted(sizes); total = sum(sizes.values()); want = fraction * total
    body = names[:-1] if len(names) > 1 else names
    k = max(1, round(want / (total / len(names))))
    k = min(k, len(body))
    idx = sorted({int((i + 0.5) * len(body) / k) for i in range(k)})
    return [body[i] for i in idx]


def token_stream(texts, encode):
    for t in texts:
        yield from encode(t)
        yield EOS_ID


def take(stream, n):
    """Exactly n token ids from the stream (error if it runs dry)."""
    out = np.empty(n, dtype=np.uint16); i = 0
    for tok in stream:
        out[i] = tok; i += 1
        if i == n: return out
    raise SystemExit(f"math slice too small: needed {n} tokens, had {i}. Build more (build_math_slice.py --target-tokens) or lower --fraction.")


def read_texts(path):
    for line in open(os.path.expanduser(path), encoding="utf-8"):
        if line.strip(): yield json.loads(line)["text"]


def build(packed, out, math_texts, heldout_texts, encode, fraction, vocab):
    packed, out = Path(packed), Path(out)
    man = json.loads((packed / "pack_manifest.json").read_text())
    train = sorted(packed.glob("train_*.bin")); sizes = {p.name: p.stat().st_size // 2 for p in train}
    replaced = choose_replaced(sizes, fraction)
    if out.exists() and any(out.iterdir()): raise SystemExit(f"{out} is not empty: use a new directory")
    out.mkdir(parents=True, exist_ok=True)
    need = sum(sizes[n] for n in replaced)
    stream = token_stream(math_texts, encode)
    try:
        for n in replaced:
            a = take(stream, sizes[n])
            if int(a.max()) >= vocab: raise SystemExit(f"token id >= vocab {vocab} in math shard {n}")
            a.tofile(out / n)
    except SystemExit:
        import shutil; shutil.rmtree(out, ignore_errors=True)       # never leave a half-built arm that looks complete
        raise
    for p in sorted(packed.glob("*.bin")):
        if p.name not in replaced: (out / p.name).symlink_to(p.resolve())
    held = np.fromiter(token_stream(heldout_texts, encode), dtype=np.uint16)
    (out / "extra_eval").mkdir(); held.tofile(out / "extra_eval" / "math_heldout.bin")
    per = dict(man.get("shard_sha256", {}))
    for n in replaced: per[n] = sha256_file(out / n)
    man["shard_sha256"] = per
    man["dataset_fingerprint"] = fingerprint({k: v for k, v in per.items() if k.startswith(("train_", "valid_"))})
    man["math_arm"] = {"fraction_requested": fraction, "replaced_shards": replaced, "replaced_tokens": need, "share_of_train": round(need / sum(sizes.values()), 4),
                       "heldout_math_tokens": int(len(held)), "parent_packed": str(packed.resolve()), "total_train_tokens_unchanged": True}
    (out / "pack_manifest.json").write_text(json.dumps(man, indent=1))
    return man["math_arm"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packed", required=True); ap.add_argument("--math", required=True); ap.add_argument("--heldout", required=True)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--out", required=True); ap.add_argument("--fraction", type=float, default=0.08)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer))
    want = json.loads((Path(a.packed) / "pack_manifest.json").read_text()).get("tokenizer_sha256")
    have = sha256_file(os.path.expanduser(a.tokenizer))
    if want and want != have: sys.exit(f"tokenizer mismatch: packed data used {want[:12]}, you gave {have[:12]}")
    info = build(a.packed, a.out, read_texts(a.math), read_texts(a.heldout), lambda t: tk.encode(t).ids, a.fraction, tk.get_vocab_size())
    print(json.dumps(info, indent=1))
    print("Next: python tools/verify_packed.py", a.out, " (hashes/tokens), then train arm B with the SAME cfg_124m and seed as arm A.")


if __name__ == "__main__":
    main()
