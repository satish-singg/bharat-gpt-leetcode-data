#!/usr/bin/env python3
"""Upload what the pod needs for the SFT + exec-eval session to the PRIVATE model repo SATISH-SINGH/cs-ckpt-backup (folder sft_bundle/).

  export HF_TOKEN=...      # typed in the terminal only; a token with WRITE access
  python3 tools/upload_sft_bundle.py --dry-run     # lists files and sizes, no network
  python3 tools/upload_sft_bundle.py               # uploads
  unset HF_TOKEN

Run from the kit root. Uploads: pod_bundle.zip (phase0/sft, eval_framework/exec_track, the two doctest task files), the tokenizer, the four paired teacher files
and tools/pod_sft_session.sh. The arm A checkpoint is already in the repo (arms/armA.pt)."""
import argparse, os, sys, zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
HOME = Path.home()
REPO = "SATISH-SINGH/cs-ckpt-backup"


def bundle_members():
    out = []
    for pat in ("phase0/sft/*.py", "phase0/sft/*.md", "eval_framework/exec_track/*.py", "eval_framework/exec_track/*.md",
                "results/exec_track/doctest_unseen.jsonl", "results/exec_track/doctest_seen.jsonl"):
        out += sorted(KIT.glob(pat))
    return out


def kit_members():
    """The whole kit (code only) so a brand-new pod works even if /workspace/kit is gone."""
    out = []
    for top in ("phase0", "eval_framework"):
        for p in sorted((KIT / top).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pt", ".bin", ".pyc"):
                out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HOME / "cs-data" / "cs-v5"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    data = Path(a.data)
    members = bundle_members()
    names = {p.name for p in members}
    need = {"sft_train.py", "sft_data.py", "cli.py", "generate_completions.py", "doctest_unseen.jsonl"}
    if need - names:
        sys.exit(f"missing from the kit: {sorted(need - names)}  (run from the kit root after copying the new files in)")
    teacher = [data / "part2_clean" / f"teacher_{s}_paired_{v}.jsonl" for s in ("train", "heldout") for v in ("direct", "reasoning")]
    singles = [(data / "tok" / "tokenizer.json", "sft_bundle/tokenizer.json"), (KIT / "tools" / "pod_sft_session.sh", "sft_bundle/pod_sft_session.sh")]
    singles += [(p, f"sft_bundle/part2_clean/{p.name}") for p in teacher]
    missing = [str(p) for p, _ in singles if not p.is_file()]
    zpath = Path(os.environ.get("TMPDIR", "/tmp")) / "pod_bundle.zip"
    kpath = Path(os.environ.get("TMPDIR", "/tmp")) / "kit_full.zip"
    kmem = kit_members()
    print(f"bundle: {len(members)} files -> {zpath};  full kit: {len(kmem)} files ({sum(p.stat().st_size for p in kmem) / 1e6:.1f} MB) -> {kpath}")
    for p, r in singles:
        print(f"  {p.name:45s} {p.stat().st_size / 1e6 if p.is_file() else 0:9.1f} MB  -> {r}")
    if missing:
        sys.exit("MISSING: " + ", ".join(missing))
    if a.dry_run:
        return
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        sys.exit("set HF_TOKEN first (type it in this terminal; never paste it in chat)")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in members:
            z.write(p, p.relative_to(KIT).as_posix())
    with zipfile.ZipFile(kpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in kmem:
            z.write(p, p.relative_to(KIT).as_posix())
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    api.upload_file(path_or_fileobj=str(zpath), path_in_repo="sft_bundle/pod_bundle.zip", repo_id=REPO)
    api.upload_file(path_or_fileobj=str(kpath), path_in_repo="sft_bundle/kit_full.zip", repo_id=REPO)
    for p, r in singles:
        print("uploading", r, flush=True)
        api.upload_file(path_or_fileobj=str(p), path_in_repo=r, repo_id=REPO)
    print("done. Now: unset HF_TOKEN")


if __name__ == "__main__":
    main()
