#!/usr/bin/env python3
"""Verify a packed/ folder against its pack_manifest.json (run it on the rented GPU right after downloading the data).

  python tools/verify_packed.py /path/to/packed            # sha256 of every shard + token counts + file list
  python tools/verify_packed.py /path/to/packed --ids      # additionally read every shard: ids < vocab and an EOS (id 3) present (slow, reads all data)

Exit code 0 = everything matches; 1 = a problem (each one is printed). Only train_*, valid_* and eval_frozen_* shards are considered.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

EOS_ID = 3


def sha256_file(p, chunk=1 << 24):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("packed"); ap.add_argument("--ids", action="store_true")
    a = ap.parse_args(); d = Path(a.packed)
    man = json.loads((d / "pack_manifest.json").read_text()); vocab = man["vocab"]; want = man["shard_sha256"]
    bad = []
    have = sorted(p.name for p in d.glob("*.bin"))
    for n in sorted(set(want) - set(have)): bad.append(f"MISSING shard listed in manifest: {n}")
    for n in sorted(set(have) - set(want)): bad.append(f"EXTRA shard not in manifest: {n}")
    tokens = {"train": 0, "valid": 0, "eval_frozen": 0}
    for i, n in enumerate(sorted(set(have) & set(want))):
        p = d / n
        if sha256_file(p) != want[n]: bad.append(f"HASH MISMATCH: {n}")
        split = next((s for s in tokens if n.startswith(s + "_")), None)
        if split is None: bad.append(f"unrecognised shard name: {n}"); continue
        tokens[split] += p.stat().st_size // 2
        if a.ids:
            x = np.fromfile(p, dtype=np.uint16)
            if x.size and int(x.max()) >= vocab: bad.append(f"TOKEN ID >= vocab in {n}")
            if not (x == EOS_ID).any(): bad.append(f"no EOS (id {EOS_ID}) in {n}")
        if (i + 1) % 50 == 0: print(f"  checked {i + 1} shards ...", flush=True)
    for s, t in tokens.items():
        exp = man["splits"].get(s, {}).get("tokens", 0)
        print(f"{s:12s} tokens on disk: {t:>15,} | manifest: {exp:>15,}")
        if t != exp: bad.append(f"TOKEN COUNT differs for {s}: disk {t} vs manifest {exp}")
    print("OK: all shards match the manifest" if not bad else "PROBLEMS:\n  " + "\n  ".join(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
