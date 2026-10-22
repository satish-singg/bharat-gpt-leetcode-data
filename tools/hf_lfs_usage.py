#!/usr/bin/env python3
"""READ-ONLY report of the large files Hugging Face stores for your repos, including OLD versions that no longer appear in the file list
(deleted or overwritten files stay in the repo history and may still count against the private-storage quota). Deletes nothing.

  read -s -p "HF token: " HF_TOKEN; export HF_TOKEN; echo
  python3 tools/hf_lfs_usage.py --repo SATISH-SINGH/cs-ckpt-backup --repo SATISH-SINGH/cs-v5-data:dataset --repo SATISH-SINGH/cs-transfer:dataset

'Referenced' = the file's SHA-256 is used by a file in the current head. Anything unreferenced is old history."""
import argparse, os, sys


def classify(lfs_files, head_sha):
    ref = [f for f in lfs_files if f.file_oid in head_sha]
    unref = [f for f in lfs_files if f.file_oid not in head_sha]
    return ref, unref


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", action="append", required=True, help="repeatable; NAME for a model repo, NAME:dataset for a dataset repo")
    a = ap.parse_args()
    tok = os.environ.get("HF_TOKEN")
    if not tok: sys.exit("set HF_TOKEN in this shell first (type it yourself; never paste it in chat)")
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    if not hasattr(api, "list_lfs_files"): sys.exit("huggingface_hub too old (needs list_lfs_files): pip install -U huggingface_hub")
    grand = 0
    for spec in a.repo:
        repo, _, kind = spec.partition(":"); kind = kind or "model"
        info = (api.model_info if kind == "model" else api.dataset_info)(repo, files_metadata=True)
        head = {(s.lfs.get("sha256") if isinstance(s.lfs, dict) else getattr(s.lfs, "sha256", None)) for s in info.siblings if s.lfs}
        lfs = list(api.list_lfs_files(repo, repo_type=kind))
        ref, unref = classify(lfs, head)
        r, u = sum(f.size for f in ref) / 1e9, sum(f.size for f in unref) / 1e9
        grand += u
        print(f"{repo} ({kind}): {len(lfs)} large files stored = {r + u:.1f} GB;  in current head {len(ref)} = {r:.1f} GB;  OLD/unreferenced {len(unref)} = {u:.1f} GB")
        for f in sorted(unref, key=lambda f: -f.size)[:8]: print(f"     old: {f.size / 1e9:6.2f} GB  {f.filename}  pushed {getattr(f, 'pushed_at', '?')}")
    print(f"total old/unreferenced across listed repos: {grand:.1f} GB (nothing deleted)")


if __name__ == "__main__":
    main()
