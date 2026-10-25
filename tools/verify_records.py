#!/usr/bin/env python3
"""Verification pipeline: gives every record an explicit status and a manifest. Reuses the existing runners (no new execution code):
  examples mode : LeetCode-style `class Solution` records; runs the statement examples (Python: tools/build_leetcode_corpus.run_examples, Java: tools/java_examples.run)
  stdio mode    : complete programs with tests [{"stdin","stdout"}] (python / java / cpp) through eval_framework/runners/code_runner.py

Input JSONL (one record per line): {"id","language","code"} plus
  examples mode: "statement" (text with Input:/Output: blocks) and optional "signature" (gives the method name)
  stdio mode   : "tests": [{"stdin","stdout"}], optional "time_limit_s"
Output JSONL, same order: {"id","status","reason","code_sha256","tests_sha256","examples_total","examples_passed","order_insensitive","toolchain","isolation","limits","runner_version"}

Status values (never skipped, never upgraded without evidence):
  collected             not run (no parseable examples / unsupported types / missing tool)  - reason says why
  quarantined           syntax or compile error, an example/test failed, timeout or crash   - reason says which
  public_tests_passed   every runnable example/test passed (examples mode never goes higher)
  verified              stdio mode only: all tests passed AND at least --min-tests tests (default 8). This is the WEAK gate of this version; stress / differential
                        tests will raise it later and the runner_version field changes when they do.
The whole process re-executes itself inside `unshare -rn` (no network) when possible; the manifest says whether that worked.
  python3 tools/verify_records.py --mode examples --in verify/pending_1_of_6.jsonl --out verify/results/runner_pending_1_of_6.jsonl"""
import argparse, ast, hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]
RUNNER_VERSION = "verify_records/1 (examples + stdio; no stress tests)"


DISPLAY_IN = re.compile(r"[A-Za-z_]\w*\s*(\[\])?\s*=\s*\S")


def sha(s): return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def toolchain():
    out = {}
    for name, cmd in (("python", ["python3", "--version"]), ("javac", ["javac", "-version"]), ("java", ["java", "-version"]), ("g++", ["g++", "--version"])):
        if shutil.which(cmd[0]) is None: out[name] = None; continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            out[name] = [l for l in (r.stdout + r.stderr).splitlines() if not l.startswith("Picked up")][0].strip()
        except Exception as e: out[name] = f"error:{type(e).__name__}"
    return out


def reexec_isolated():
    """Run this very command inside a fresh network namespace if the machine allows it. Returns the isolation label."""
    if os.environ.get("VR_ISOLATION"): return os.environ["VR_ISOLATION"]
    un = shutil.which("unshare")
    for flags, label in ((["-n"], "netns(root)"), (["-rn"], "netns(userns)")):
        if un and subprocess.run([un] + flags + ["true"], capture_output=True).returncode == 0:
            env = dict(os.environ, VR_ISOLATION=label)
            os.execvpe(un, [un] + flags + ["--", sys.executable] + sys.argv, env)
    return "none"


def py_method(code, sig, nargs):
    if sig:
        m = re.search(r"def\s+(\w+)\s*\(", sig)
        if m: return m.group(1)
    try: tree = ast.parse(code)
    except SyntaxError: return None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            cands = [f for f in node.body if isinstance(f, ast.FunctionDef) and not f.name.startswith("_")]
            for f in cands:
                if len(f.args.args) - 1 == nargs: return f.name
            return cands[0].name if cands else None
    return None


def _split_top(text, sep):
    """Split on `sep` outside brackets and string quotes."""
    out, depth, q, cur = [], 0, None, ""
    for ch in text:
        if q:
            cur += ch
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; cur += ch; continue
        if ch in "([{": depth += 1
        elif ch in ")]}": depth -= 1
        if ch == sep and depth == 0: out.append(cur); cur = ""
        else: cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def param_names(sig):
    m = re.search(r"\(([^)]*)\)", sig or "")
    if not m: return []
    names = []
    for part in _split_top(m.group(1), ","):
        part = part.strip()
        if not part or part == "self": continue
        if ":" in part: names.append(part.split(":")[0].strip())            # python: name: type
        else: names.append(part.split()[-1].strip())                         # java: Type name
    return names


def normalise_statement(st, sig=None):
    """ChatGPT-written statements give examples as `Examples: [2,2,3,2] -> 3; a = 1, b = 2 -> out.`; the shared parser wants `Input: name = value, ...\nOutput: value` blocks.
    Positional values are bound to the parameter names of the signature (only when the counts agree)."""
    if "Input:" in st: return st
    m = re.search(r"Examples?:\s*(.*)", st, flags=re.S)
    if not m: return st
    names = param_names(sig); blocks = []
    for piece in _split_top(m.group(1).strip(), ";"):
        if "->" not in piece: continue
        lhs, rhs = piece.split("->", 1)
        lhs, rhs = lhs.strip(), rhs.strip().rstrip(".").strip()
        if not re.match(r"^\w+\s*=", lhs):
            vals = _split_top(lhs, ",")
            if names and len(vals) == len(names): lhs = ", ".join(f"{n} = {v}" for n, v in zip(names, vals))
            else: continue
        blocks.append(f"Input: {lhs}\nOutput: {rhs}\n")
    return st + "\n\n" + "\n".join(blocks) if blocks else st


def jsonable(x):
    try: json.dumps(x); return True
    except (TypeError, ValueError): return False


def run_examples_mode(recs, workers):
    from build_leetcode_corpus import parse_examples, run_examples
    import java_examples
    out = {}; pyjobs = []; jjobs = []
    for r in recs:
        ex = parse_examples(normalise_statement(r.get("statement", ""), r.get("signature")))
        ex = [e for e in ex if jsonable(e)]               # an example written with "..." (e.g. nums = [1,2,...]) parses to Ellipsis: it cannot be run, drop it instead of crashing the whole batch
        r["_ex"] = ex
        if not ex: out[r["id"]] = ("collected", "no_parseable_examples", 0, 0, 0); continue
        if r["language"].startswith("python"):
            try: compile(r["code"], "<rec>", "exec")
            except SyntaxError as e: out[r["id"]] = ("quarantined", f"syntax_error:{e.msg}", len(ex), 0, 0); continue
            m = py_method(r["code"], r.get("signature"), len(ex[0][0]))
            if not m: out[r["id"]] = ("collected", "no_method_found", len(ex), 0, 0); continue
            pyjobs.append({"id": r["id"], "code": r["code"], "method": m, "examples": [[a, e] for a, e in ex]})
        elif r["language"] == "java":
            jjobs.append({"id": r["id"], "code": r["code"], "examples": ex, "hint": None})
        else: out[r["id"]] = ("collected", f"unsupported_language:{r['language']}", len(ex), 0, 0)
    res = run_examples(pyjobs, workers=workers) if pyjobs else {}
    for j in pyjobs:
        x = res.get(j["id"])
        if x is None: out[j["id"]] = ("quarantined", "harness_no_result(timeout_or_crash)", len(j["examples"]), 0, 0); continue
        tot, ok, un = x.get("total", 0), x.get("passed", 0), x.get("unordered", 0)
        fe = str(x.get("firsterr") or "")
        if x.get("error") == "NameError" or (fe.startswith("TypeError") and "argument" in fe) or fe.startswith("NameError"):   # ListNode/TreeNode helpers or misparsed arguments: the HARNESS cannot run it, which says nothing about the code
            out[j["id"]] = ("collected", "harness_unsupported:" + (fe or x["error"])[:70], tot or len(j["examples"]), ok, un)
        elif x.get("error"): out[j["id"]] = ("quarantined", f"error:{x['error']}", tot or len(j["examples"]), ok, un)
        elif tot and ok + un == tot: out[j["id"]] = ("public_tests_passed", "all_examples_passed" + ("(order_insensitive:%d)" % un if un else ""), tot, ok, un)
        else: out[j["id"]] = ("quarantined", "example_failed:" + str(x.get("firsterr") or f"{ok}/{tot}"), tot, ok, un)
    jr = java_examples.run(jjobs) if jjobs else {}
    for j in jjobs:
        x = jr.get(j["id"], {})
        if x.get("skip"): out[j["id"]] = ("collected", "java_" + str(x["skip"]), len(j["examples"]), 0, 0); continue
        tot, ok, un = x.get("total", 0), x.get("passed", 0), x.get("unordered", 0)
        if x.get("error"): out[j["id"]] = ("quarantined", "java_error:" + str(x["error"])[:80], tot or len(j["examples"]), ok, un)
        elif tot and ok + un == tot: out[j["id"]] = ("public_tests_passed", "all_examples_passed" + ("(order_insensitive:%d)" % un if un else ""), tot, ok, un)
        else: out[j["id"]] = ("quarantined", "example_failed:" + str(x.get("firsterr") or f"{ok}/{tot}"), tot, ok, un)
    return out


def run_stdio_mode(recs, min_tests):
    from eval_framework.runners.code_runner import run_code, missing_tools
    out = {}
    for r in recs:
        lang = {"python3": "python", "python": "python", "java": "java", "cpp": "cpp", "c++": "cpp"}.get(r["language"].lower())
        tests = r.get("tests") or []
        if not lang or not tests: out[r["id"]] = ("collected", "no_tests_or_unsupported_language", len(tests), 0, 0); continue
        if any(DISPLAY_IN.match((t.get("stdin") or "").lstrip()) for t in tests):    # GfG-style "N = 5 / A = {1,2}" example text, not what a stdin program reads: the TEST cannot judge a program, which says nothing about the code
            out[r["id"]] = ("collected", "tests_in_display_format(name = value)", len(tests), 0, 0); continue
        if missing_tools(lang): out[r["id"]] = ("collected", "toolchain_missing:" + ",".join(missing_tools(lang)), len(tests), 0, 0); continue
        item = {"language": lang, "tests": json.dumps([{"name": f"t{i}", "stdin": t["stdin"], "stdout": t["stdout"]} for i, t in enumerate(tests)]),
                "time_limit_s": r.get("time_limit_s", 10), "item_timeout_s": 60}
        res = run_code(item, r["code"] if r["code"].endswith("\n") else r["code"] + "\n")["details"]
        if res.get("error") == "compile_error": out[r["id"]] = ("quarantined", "compile_error:" + res.get("stderr", "")[:120].replace("\n", " "), len(tests), 0, 0); continue
        tot, ok = res["total"], res["passed"]
        bad = [t["status"] for t in res["tests"] if not t["pass"]]
        if ok == tot: out[r["id"]] = ("verified" if tot >= min_tests else "public_tests_passed", f"all_{tot}_tests_passed", tot, ok, 0)
        else: out[r["id"]] = ("quarantined", f"{tot - ok}/{tot}_tests_failed({bad[0]})", tot, ok, 0)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["examples", "stdio"], required=True); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--min-tests", type=int, default=8)
    ap.add_argument("--require-isolation", action="store_true", help="exit when no network namespace is available")
    a = ap.parse_args()
    iso = reexec_isolated()
    if iso == "none" and a.require_isolation: sys.exit("no network isolation available on this machine (unshare failed); refusing to run untrusted code")
    recs = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    res = run_examples_mode(recs, a.workers) if a.mode == "examples" else run_stdio_mode(recs, a.min_tests)
    tc = toolchain(); limits = {"mode": a.mode, "min_tests": a.min_tests}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    counts = {}
    with open(a.out, "w", encoding="utf-8") as g:
        for r in recs:
            st, why, tot, ok, un = res.get(r["id"], ("collected", "not_processed", 0, 0, 0)); counts[st] = counts.get(st, 0) + 1
            tests_src = json.dumps(r.get("tests"), sort_keys=True) if a.mode == "stdio" else r.get("statement", "")
            g.write(json.dumps({"id": r["id"], "status": st, "reason": why, "code_sha256": sha(r["code"]), "tests_sha256": sha(tests_src), "examples_total": tot,
                                "examples_passed": ok, "order_insensitive": un, "toolchain": tc, "isolation": iso, "limits": limits, "runner_version": RUNNER_VERSION},
                               ensure_ascii=False) + "\n")
    print(json.dumps({"records": len(recs), "by_status": counts, "isolation": iso}))
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    main()
