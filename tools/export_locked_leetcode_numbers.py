#!/usr/bin/env python3
"""Write the LeetCode problem numbers of the locked evaluation split (newfacade/LeetCodeDataset TEST split, the source of the locked LeetCode tasks), one per line.
Give this file to any agent that collects LeetCode problems: those problems must never be used for training.
  python3 tools/export_locked_leetcode_numbers.py --out ~/ProjectAI/data/test/locked_leetcode_numbers.txt        (needs `datasets` and network)"""
import argparse, os
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
from datasets import load_dataset
nums = sorted({int(x) for x in load_dataset("newfacade/LeetCodeDataset", split="test")["question_id"]})
out = os.path.expanduser(a.out); os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, "w").write("\n".join(map(str, nums)) + "\n"); print(len(nums), "numbers ->", out, "first", nums[:8])
