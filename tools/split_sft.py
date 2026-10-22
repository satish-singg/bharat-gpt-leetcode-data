#!/usr/bin/env python3
"""Deterministic train / held-out split of an SFT jsonl (rows with a "text" field "Question: <Q>\\n\\nAnswer:\\n<A>").
The split is by a hash of the QUESTION, so a given question always lands on the same side (no leakage between train and held-out) and re-running gives the same files.

  python3 split_sft.py --in sft_v2.jsonl --train sft_v2_train.jsonl --val sft_v2_val.jsonl [--val-per-mille 5]
Standard library only, so it runs on the rental pod."""
import argparse, hashlib, json, sys


def side(text, per_mille):
    q = text.split("\n\nAnswer:\n", 1)[0]
    return "val" if int(hashlib.sha256(q.encode("utf-8")).hexdigest(), 16) % 1000 < per_mille else "train"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--train", required=True); ap.add_argument("--val", required=True)
    ap.add_argument("--val-per-mille", type=int, default=5, help="about this many rows per 1,000 go to held-out (default 5 = 0.5%%)")
    a = ap.parse_args()
    n = {"train": 0, "val": 0}
    with open(a.inp, encoding="utf-8") as f, open(a.train, "w", encoding="utf-8") as ft, open(a.val, "w", encoding="utf-8") as fv:
        for line in f:
            if not line.strip(): continue
            s = side(json.loads(line)["text"], a.val_per_mille)
            (ft if s == "train" else fv).write(line if line.endswith("\n") else line + "\n"); n[s] += 1
    print(f"train {n['train']:,}  val {n['val']:,}")


if __name__ == "__main__":
    main()
