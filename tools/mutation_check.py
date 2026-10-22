#!/usr/bin/env python3
"""Mutation check: proves that the regression tests for the review fixes CATCH the bugs they were written for.

For every fix listed in MUTATIONS, this script copies the kit to a temporary directory, puts the old bug back (an exact text
replacement in one or more files), runs the tests that should catch it, and records which of them fail. A mutation that no
test catches is reported as NOT CAUGHT and the script exits 1. Nothing in the kit itself is modified.

  python tools/mutation_check.py                          # all mutations, report on stdout
  python tools/mutation_check.py --out MUTATION_REPORT.json
  python tools/mutation_check.py --only launcher          # mutations whose name contains "launcher"

Some tests need the full code sandbox (sandbox.strong()); where it is missing they are skipped, and a mutation that only
those tests can catch is reported as NOT OBSERVABLE HERE (not as caught). Runs on CPU, no torch needed; about 1-2 minutes.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]

# (name, review it answers, [(file relative to the kit, old text, new text), ...], test ids run from phase0/gate)
MUTATIONS = [
    # ---- review of v4.4 (fixed in v4.5)
    ("freezer applies phase0_overrides.yaml", "v4.4 P1",
     [("phase0/gate/arm_plan.py", 'return ["--no-overrides", "--micro-batch"', 'return ["--micro-batch"')],
     ["test_gate_e2e.ArmPlanFromRealArms", "test_gate_e2e.LauncherAgreement"]),
    ("micro-batch / world not in the arm identity", "v4.4 P1",
     [("phase0/gate/arm_plan.py", '"compile", "micro_batch", "world")', '"compile")')],
     ["test_gate_e2e.ArmPlan"]),
    ("report ignores the PID namespace", "v4.4 P1",
     [("phase0/gate/gate1_report.py", "missing = [k for k in P.SANDBOX_LAYERS if", "missing = [k for k in P.SANDBOX_LAYERS[:3] if")],
     ["test_gate_e2e.ArmPlan"]),
    ("model-loading code not frozen", "v4.4 P1",
     [("phase0/gate/protocol.py", ', "../generate.py", "../train_phase0.py", "../phase0_utils.py")', ")")],
     ["test_gate_e2e.ProtocolSchema"]),
    ("digest with a trailing newline accepted", "v4.4 P2",
     [("phase0/gate/protocol.py", "HEX64.fullmatch(v) is not None", "bool(re.match(r'^[0-9a-fA-F]{64}$', v))")],
     ["test_gate_e2e.ProtocolSchema"]),
    ("framework imported from its install path", "found in v4.5",
     [("phase0/gate/framework_items.py", 'job = json.dumps({"runners": runner_sources(framework),',
       'job = json.dumps({"runners": {}, "framework": str(Path(framework).resolve()),'),
      ("phase0/gate/framework_items.py", '    "sys.path.insert(0, os.getcwd())\\n"', '    "sys.path.insert(0, job[\'framework\'])\\n"')],
     ["test_gate_e2e.FrameworkSandbox", "test_gate.FrameworkRunnerFailure"]),
    # ---- review of v4.5 (fixed in v4.6)
    ("arm plan accepts world size 2 (describe)", "v4.5 P2",
     [("phase0/gate/arm_plan.py", "    if int(world) != LAUNCH_WORLD:\n        raise PlanError(", "    if int(world) < 1:\n        raise PlanError(")],
     ["test_gate_e2e.ArmPlanFromRealArms"]),
    ("arm plan accepts world size 2 (plan check)", "v4.5 P2",
     [("phase0/gate/arm_plan.py", '        if a.get("world") != LAUNCH_WORLD:', "        if False:")],
     ["test_gate_e2e.ArmPlan"]),
    ("launcher hash not required in the plan", "v4.5 P2",
     [("phase0/gate/arm_plan.py", '    if not P._hex(plan.get("launcher_sha256")):', "    if False:")],
     ["test_gate_e2e.ArmPlan"]),
    ("launcher hash not compared at Gate 1", "v4.5 P2",
     [("phase0/gate/arm_plan.py", '    if meta.get("launcher_sha256") != plan.get("launcher_sha256"):', "    if False:")],
     ["test_gate_e2e.ArmPlan"]),
    ("check-launch ignores the launcher hash", "v4.5 P2",
     [("phase0/gate/arm_plan.py", '    if U.launcher_sha256(launcher) != plan.get("launcher_sha256"):', "    if False:")],
     ["test_gate_e2e.LauncherAgreement"]),
    ("resume across code/launcher change keeps the new hash", "found in v4.6",
     [("phase0/phase0_utils.py", '    return current if saved == current else "mixed"', "    return current")],
     ["test_gate_e2e.ArmPlan"]),
    ("run_final.sh skips check-launch", "v4.5 P2",
     [("phase0/scale/run_final.sh", 'if [ -n "${ARM_PLAN:-}${ARM_PLAN_SHA256:-}${ARM:-}" ] || [ "${GATE1:-}" = "1" ]; then', "if false; then")],
     ["test_gate_e2e.LauncherAgreement"]),
    ("run_final.sh skips the check when only some Gate 1 variables are set", "v4.7 operational caveat",
     [("phase0/scale/run_final.sh", 'if [ -n "${ARM_PLAN:-}${ARM_PLAN_SHA256:-}${ARM:-}" ] || [ "${GATE1:-}" = "1" ]; then', 'if [ -n "${ARM_PLAN:-}" ]; then')],
     ["test_gate_e2e.LauncherAgreement"]),
    ("dataset fingerprint caches a racily-fresh file (coarse-timestamp filesystems)", "found on the user's machine, v4.7",
     [("phase0/phase0_utils.py", "if time.time_ns() - max(st.st_mtime_ns, st.st_ctime_ns) >= RACY_NS:", "if True:")],
     ["test_phase0_logic.T.test_fingerprint_on_a_filesystem_with_coarse_timestamps", "test_phase0_logic.T.test_old_files_are_cached_and_fresh_files_are_not"], "phase0"),
    ("run_final.sh does not export CS_LAUNCHER", "v4.5 P2",
     [("phase0/scale/run_final.sh", 'export CS_LAUNCHER="$HERE/run_final.sh"', "true")],
     ["test_gate_e2e.LauncherAgreement"]),
    # ---- review of v4.6 (fixed in v4.7)
    ("EXTRA_ARGS allowlist off", "v4.6 P2",
     [("phase0/gate/arm_plan.py", '    out, i, toks = [], 0, list(extra_argv)\n', "    return []\n    out, i, toks = [], 0, list(extra_argv)\n")],
     ["test_gate_e2e.LauncherAgreement"]),
    ("EXTRA_ARGS allowlist and effective resume/out-dir checks off (the v4.6 state)", "v4.6 P2",
     [("phase0/gate/arm_plan.py", '    out, i, toks = [], 0, list(extra_argv)\n', "    return []\n    out, i, toks = [], 0, list(extra_argv)\n"),
      ("phase0/gate/arm_plan.py", "    for k, v in LAUNCHER_REQUIRED.items():                 # the EFFECTIVE values, after EXTRA_ARGS",
       "    for k, v in {}.items():                 # the EFFECTIVE values, after EXTRA_ARGS"),
      ("phase0/gate/arm_plan.py", '    for k in ("out_dir", "data_dir", "cfg_dir", "log_every", "micro_batch"):', "    for k in ():")],
     ["test_gate_e2e.LauncherAgreement"]),
    ("effective resume / out-dir checks off (allowlist still on)", "v4.6 P2",
     [("phase0/gate/arm_plan.py", "    for k, v in LAUNCHER_REQUIRED.items():                 # the EFFECTIVE values, after EXTRA_ARGS",
       "    for k, v in {}.items():                 # the EFFECTIVE values, after EXTRA_ARGS")],
     ["test_gate_e2e.LauncherAgreement"]),
]


def run_tests(gate_dir, tests, cwd=None):
    """Run the tests with NO bytecode cache. A mutation and the next one can change a file within the same second by the
    same number of bytes; Python's .pyc check (mtime in seconds + size) would then run the PREVIOUS mutation's cached code
    and report a wrong result (this happened while writing this script). So caches are deleted and never written."""
    root = Path(gate_dir).parents[1]
    for c in root.rglob("__pycache__"):
        shutil.rmtree(c, ignore_errors=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v"] + tests, cwd=cwd or gate_dir, capture_output=True, text=True, timeout=1200,
                       stdin=subprocess.DEVNULL, env=env)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \(", r.stderr, re.M)))
    skipped = sorted(set(re.findall(r"^(\w+) \([^)]*\)(?:\n.*?)? \.\.\. skipped", r.stderr, re.M)))
    ran = re.search(r"^Ran (\d+) tests?", r.stderr, re.M)
    return r.returncode, failed, skipped, int(ran.group(1)) if ran else 0, r.stderr[-1500:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write the report as JSON here")
    ap.add_argument("--only", help="run only mutations whose name contains this text")
    a = ap.parse_args()
    work = Path(tempfile.mkdtemp(prefix="cs_mut_")) / "kit"
    shutil.copytree(KIT, work, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "TEST_REPORT_*", "MUTATION_REPORT*"))
    os.chmod(work.parent, 0o755)
    gate = work / "phase0" / "gate"
    report = {"kit": str(KIT), "python": sys.version.split()[0], "uid": os.getuid(), "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "baseline": None, "mutations": []}
    all_tests = sorted({t for m in MUTATIONS for t in m[3] if len(m) < 5})
    rc, failed, skipped, ran, tail = run_tests(gate, all_tests)
    for m_ in MUTATIONS:                                 # mutations with their own working directory (5th field) get their own baseline
        if len(m_) >= 5:
            rc2, f2, s2, r2, t2 = run_tests(gate, m_[3], cwd=work / m_[4])
            ran += r2; failed += f2; skipped += s2
            if rc2 != 0: rc, tail = rc2, t2
    report["baseline"] = {"tests": all_tests, "ran": ran, "failed": failed, "skipped": skipped, "ok": rc == 0}
    print(f"baseline (no mutation): {ran} tests, failed {failed or 'none'}, skipped {len(skipped)}", flush=True)
    if rc != 0:
        print(tail); print("BASELINE FAILS: fix the tests first"); sys.exit(2)
    bad = 0
    for name, review, edits, tests, *rest in MUTATIONS:
        if a.only and a.only not in name:
            continue
        originals = {}
        try:
            for rel, old, new in edits:
                f = work / rel
                if rel not in originals:                      # keep the unmutated text to restore afterwards
                    originals[rel] = f.read_text(encoding="utf-8")
                txt = f.read_text(encoding="utf-8")           # a second edit of the same file applies on top of the first
                if txt.count(old) != 1:
                    raise SystemExit(f"mutation {name!r}: the text to replace occurs {txt.count(old)} times in {rel}: update this script")
                f.write_text(txt.replace(old, new), encoding="utf-8")
            rc, failed, skipped, ran, tail = run_tests(gate, tests, cwd=(work / rest[0]) if rest else None)
        finally:
            for rel, txt in originals.items():
                (work / rel).write_text(txt, encoding="utf-8")
        status = "CAUGHT" if failed else ("NOT OBSERVABLE HERE (tests skipped)" if skipped else "NOT CAUGHT")
        if status == "NOT CAUGHT":
            bad += 1
        report["mutations"].append({"name": name, "review": review, "files": sorted({e[0] for e in edits}), "tests": tests,
                                    "ran": ran, "failing_tests": failed, "skipped_tests": skipped, "status": status})
        print(f"{status:12s} [{review}] {name}: {', '.join(failed) or '-'}", flush=True)
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["all_caught"] = bad == 0
    shutil.rmtree(work.parent, ignore_errors=True)
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1))
    print("ALL MUTATIONS CAUGHT" if bad == 0 else f"{bad} MUTATION(S) NOT CAUGHT")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
