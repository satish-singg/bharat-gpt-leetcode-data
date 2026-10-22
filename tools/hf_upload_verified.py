#!/usr/bin/env python3
"""Upload ONE file to a Hugging Face repo and verify the stored copy by SHA-256 (the remote LFS hash must equal the local hash). Never deletes anything.

  read -s -p "HF token: " HF_TOKEN; export HF_TOKEN; echo
  python3 tools/hf_upload_verified.py --repo SATISH-SINGH/cs-ckpt-backup --file export/model_bf16.pt --path-in-repo run350-final/model_bf16.pt
  unset HF_TOKEN"""
import argparse, hashlib, os, sys


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True); ap.add_argument("--file", required=True); ap.add_argument("--path-in-repo", required=True); ap.add_argument("--repo-type", default="model")
    a = ap.parse_args()
    tok = os.environ.get("HF_TOKEN")
    if not tok: sys.exit("set HF_TOKEN in this shell first (type it yourself; never paste it in chat)")
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    local = sha256_file(a.file); print("local sha256", local, os.path.getsize(a.file), "bytes", flush=True)
    api.upload_file(path_or_fileobj=a.file, path_in_repo=a.path_in_repo, repo_id=a.repo, repo_type=a.repo_type)
    info = (api.model_info if a.repo_type == "model" else api.dataset_info)(a.repo, files_metadata=True)
    for s in info.siblings:
        if s.rfilename == a.path_in_repo:
            remote = (s.lfs.get("sha256") if isinstance(s.lfs, dict) else getattr(s.lfs, "sha256", None)) if s.lfs else None
            if remote is None:   # small files are stored without LFS (no hash in the listing): compare size, then content via download
                from huggingface_hub import hf_hub_download
                back = hf_hub_download(a.repo, a.path_in_repo, repo_type=a.repo_type, token=tok)
                if sha256_file(back) == local: print("VERIFIED (non-LFS file, content re-downloaded and hashed)", a.repo, a.path_in_repo); return
                sys.exit("MISMATCH: downloaded copy differs from local file")
            if remote == local: print("VERIFIED", a.repo, a.path_in_repo); return
            sys.exit(f"MISMATCH remote {remote} local {local}")
    sys.exit("uploaded file not found in the repo listing")


if __name__ == "__main__":
    main()
