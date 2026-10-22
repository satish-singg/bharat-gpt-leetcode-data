#!/usr/bin/env python3
"""Back up the Part 1 results to a PRIVATE Hugging Face dataset repo.

  export HF_TOKEN=hf_xxx            # a token with WRITE access (never paste it anywhere else)
  python upload_to_hf.py --repo YOUR_USERNAME/cs-v5-data --dry-run     # lists what would be uploaded, no network
  python upload_to_hf.py --repo YOUR_USERNAME/cs-v5-data               # uploads (safe to re-run: finished files are skipped)

Uploaded: packed/ (token shards + manifest), tok/ (tokenizer), cfg/ (rendered configs), the three reports, eval_manifest.json, my_master.yaml.
Add --with-clean to also upload clean/ (about 11 GB of cleaned text, useful if you ever want to re-pack with another tokenizer or mix).
"""
import argparse, os, sys
from pathlib import Path

HOME = Path.home()


def plan(work, eval_manifest, master, with_clean, clean_zst=False):
    allow = ["packed/*", "tok/*", "cfg/*", "plan_vs_actual.json", "clean/clean_report.json", "raw/books_report.json"]
    if with_clean:
        allow += ["clean/*"]
    elif clean_zst:
        allow += ["clean/*.zst"]          # compressed copies only (zstd -3 of each clean/*.jsonl)
    files = []
    for pat in allow:
        files += [p for p in sorted(work.glob(pat)) if p.is_file()]
    extra = [(eval_manifest, "meta/eval_manifest.json"), (master, "meta/my_master.yaml")]
    return allow, files, [(p, r) for p, r in extra if Path(p).is_file()], [str(p) for p, _ in extra if not Path(p).is_file()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="USERNAME/NAME of the private dataset repo (created if missing)")
    ap.add_argument("--work", default=str(HOME / "cs-data" / "cs-v5"))
    ap.add_argument("--eval-manifest", default=str(HOME / "cs-data" / "eval_manifest.json"))
    ap.add_argument("--master", default=str(HOME / "WorkSpace" / "test" / "GPT_FROM_SCRATCH" / "phase0" / "my_master.yaml"))
    ap.add_argument("--with-clean", action="store_true")
    ap.add_argument("--clean-zst", action="store_true", help="upload only clean/*.zst (compress clean/*.jsonl with zstd first)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)
    allow, files, extra, missing = plan(work, a.eval_manifest, a.master, a.with_clean, a.clean_zst)
    total = sum(p.stat().st_size for p in files) + sum(Path(p).stat().st_size for p, _ in extra)
    print(f"{len(files)} files under {work} + {len(extra)} extra files = {total / 1e9:.2f} GB")
    for p in files[:6] + (["..."] if len(files) > 6 else []):
        print("  ", p)
    for p, r in extra:
        print("  ", p, "->", r)
    for m in missing:
        print("  MISSING (not uploaded):", m)
    if not any("packed" in str(p) for p in files):
        sys.exit("no packed shards found: check --work")
    if a.dry_run:
        return
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        sys.exit("set HF_TOKEN first:  export HF_TOKEN=hf_xxx")
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    api.create_repo(a.repo, repo_type="dataset", private=True, exist_ok=True)
    if hasattr(api, "upload_large_folder"):          # resumable and multi-threaded: re-run after any interruption
        api.upload_large_folder(repo_id=a.repo, repo_type="dataset", folder_path=str(work), allow_patterns=allow)
    else:                                            # older huggingface_hub: plain folder upload
        for d in ("packed", "tok", "cfg"):
            api.upload_folder(repo_id=a.repo, repo_type="dataset", folder_path=str(work / d), path_in_repo=d)
        for f in ("plan_vs_actual.json",):
            api.upload_file(repo_id=a.repo, repo_type="dataset", path_or_fileobj=str(work / f), path_in_repo=f)
    for p, r in extra:
        api.upload_file(repo_id=a.repo, repo_type="dataset", path_or_fileobj=str(p), path_in_repo=r)
    print("done: https://huggingface.co/datasets/" + a.repo + "  (private)")


if __name__ == "__main__":
    main()
