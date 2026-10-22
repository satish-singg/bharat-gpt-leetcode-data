#!/usr/bin/env python3
"""Mirror a Hugging Face repo to local disk, verify every file's SHA-256 against the remote LFS hash, and optionally free the remote space.

  read -s -p "HF token: " HF_TOKEN; export HF_TOKEN; echo
  setsid nohup env -u PYTHONPATH ~/pilot-venv2/bin/python -u tools/hf_mirror.py --repo SATISH-SINGH/cs-ckpt-backup --dest ~/ckpt_mirror > ~/hf_mirror.log 2>&1 < /dev/null &
  unset HF_TOKEN
  # only after the log ends with "ALL VERIFIED" run it again with --delete-verified to free remote space (it re-checks each file first, deletes only verified ones)

Default is read-only on the remote. Files are skipped when the local copy already matches. Never prints the token."""
import argparse, hashlib, json, os, sys, time


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()


def remote_files(api, repo, repo_type):
    info = (api.model_info if repo_type == "model" else api.dataset_info)(repo, files_metadata=True)
    out = []
    for s in info.siblings:
        lfs = getattr(s, "lfs", None)
        sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
        out.append({"name": s.rfilename, "size": s.size, "sha256": sha})
    return sorted(out, key=lambda x: x["name"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True); ap.add_argument("--dest", required=True); ap.add_argument("--repo-type", default="model", choices=["model", "dataset"])
    ap.add_argument("--delete-verified", action="store_true", help="after a file is verified locally, delete it from the remote repo")
    a = ap.parse_args()
    tok = os.environ.get("HF_TOKEN")
    if not tok: sys.exit("set HF_TOKEN in this shell first (type it yourself; never paste it in chat)")
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=tok)
    dest = os.path.expanduser(a.dest); os.makedirs(dest, exist_ok=True)
    files = remote_files(api, a.repo, a.repo_type)
    print(f"{a.repo}: {len(files)} files, {sum((f['size'] or 0) for f in files) / 1e9:.1f} GB", flush=True)
    results, bad = [], 0
    for f in files:
        path = os.path.join(dest, f["name"]); t0 = time.time()
        if not (os.path.exists(path) and f["size"] is not None and os.path.getsize(path) == f["size"]):
            hf_hub_download(a.repo, f["name"], repo_type=a.repo_type, local_dir=dest, token=tok)
        got = sha256_file(path) if f["sha256"] else None
        ok = (got == f["sha256"]) if f["sha256"] else (os.path.getsize(path) == f["size"])   # small non-LFS files: size check only
        bad += (not ok)
        print(f"  {'OK ' if ok else 'BAD'} {f['name']} {(f['size'] or 0) / 1e9:.2f} GB {'sha256' if f['sha256'] else 'size-only'} {time.time() - t0:.0f}s", flush=True)
        results.append({**f, "local_sha256": got, "verified": ok, "deleted_remote": False})
        if ok and a.delete_verified:
            api.delete_file(f["name"], repo_id=a.repo, repo_type=a.repo_type, commit_message="free space: copy verified on local disk")
            results[-1]["deleted_remote"] = True; print(f"     deleted from remote: {f['name']}", flush=True)
    json.dump({"repo": a.repo, "files": results}, open(os.path.join(dest, "MIRROR_REPORT.json"), "w"), indent=1)
    print("ALL VERIFIED" if not bad else f"{bad} FILE(S) BAD - do not delete anything", flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
