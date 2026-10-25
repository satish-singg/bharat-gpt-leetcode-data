#!/usr/bin/env python3
"""Audit the ChatGPT-written problems in newproblems/batch_*.jsonl. For every problem: all required fields present, >= 3 sample tests, BOTH reference_python and brute_force_python run on every sample
and match the expected output (whitespace at line ends ignored). Also reports duplicate titles / statement openings and which key names the sample tests use.
  python3 tools/audit_newproblems.py                         (all batches, summary + first 20 failures)
  python3 tools/audit_newproblems.py --batch 0007 --verbose  (one batch, every failure)
  python3 tools/audit_newproblems.py --report review/np_audit.json   (full machine-readable list)
Exit code 1 when any problem has an issue (usable as a GitHub check)."""
import argparse, collections, concurrent.futures as cf, glob, json, os, subprocess, sys, tempfile
NEED = ["id", "title", "difficulty", "topic", "statement", "input_format", "output_format", "constraints", "sample_tests", "reference_python", "intended_complexity", "brute_force_python"]
norm = lambda s: "\n".join(x.rstrip() for x in str(s).strip().splitlines())


def run(code, stdin):
    with tempfile.TemporaryDirectory() as d:
        open(d + "/m.py", "w").write(code)
        try:
            r = subprocess.run([sys.executable, "-I", d + "/m.py"], input=stdin, capture_output=True, text=True, timeout=10, cwd=d)
            return r.returncode, r.stdout, r.stderr.strip()[-100:]
        except subprocess.TimeoutExpired: return -9, "", "timeout"


def check(r):
    o = {"id": r.get("id"), "missing": [k for k in NEED if not r.get(k)], "issues": []}
    tests = r.get("sample_tests") or []
    if len(tests) < 3: o["issues"].append(f"only {len(tests)} sample tests")
    for i, t in enumerate(tests):
        stdin, want = t.get("stdin", t.get("input", "")), t.get("stdout", t.get("output", ""))
        for name in ("reference_python", "brute_force_python"):
            if not r.get(name): continue
            rc, out, err = run(r[name], stdin)
            if rc != 0: o["issues"].append(f"{name} sample {i}: crash: {err.splitlines()[-1] if err else rc}")
            elif norm(out) != norm(want): o["issues"].append(f"{name} sample {i}: output != expected")
    return o


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="newproblems"); ap.add_argument("--batch", help="e.g. 0007"); ap.add_argument("--report"); ap.add_argument("--verbose", action="store_true"); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, f"batch_{a.batch or '*'}.jsonl")))
    recs = [json.loads(l) for f in files for l in open(f, encoding="utf-8") if l.strip()]
    with cf.ThreadPoolExecutor(a.workers) as ex: res = list(ex.map(check, recs))
    bad = [x for x in res if x["missing"] or x["issues"]]
    titles = collections.Counter(r.get("title", "").strip().lower() for r in recs)
    dups = sorted(t for t, c in titles.items() if c > 1)
    keys = collections.Counter(("stdin/stdout" if "stdin" in (r.get("sample_tests") or [{}])[0] else "input/output") for r in recs)
    print(f"problems {len(recs)}  ids unique {len({r.get('id') for r in recs})}  with an issue {len(bad)}  duplicate titles {len(dups)}  sample key names {dict(keys)}")
    for x in bad[: (len(bad) if a.verbose else 20)]: print(" ", x["id"], x["missing"] or "", x["issues"][:4])
    if a.report:
        os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
        json.dump({"problems": len(recs), "bad": bad, "duplicate_titles": dups, "sample_keys": dict(keys)}, open(a.report, "w"), indent=1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__": main()
