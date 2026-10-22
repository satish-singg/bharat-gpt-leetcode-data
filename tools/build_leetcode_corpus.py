#!/usr/bin/env python3
"""Build a LeetCode solution corpus from two public repos (no model, no network):
  Anas   github.com/AnasImloul/Leetcode-Solutions  (Unlicense)  statements, Python/Java reference solutions
  kamyu  github.com/kamyu104/LeetCode-Solutions    (MIT)        Python (py2 style) + C++ solutions, several approaches per file,
                                                               each `class Solution*` preceded by the author's  "# Time: O(..) / # Space: O(..)"  header; topic sections in 0001-1000.md etc.
Output (--out):
  problems.jsonl    number,title,slug,difficulty,statement,python_signature,java_signature,topics[]
  solutions.jsonl   one line per solution: language(python3|java|cpp), source, variant, code, time_complexity, space_complexity,
                    complexity_evidence ("author_label" or null), expected_to_pass_time_limit, examples{total,passed,unordered}, tier A|B|C|D
  sft.jsonl         {"messages":[user,assistant]} for tier A/B/C solutions (D = failed a statement example: excluded)
  report.json       counts
Tiers: A = author complexity label AND every runnable statement example passed; B = examples passed; C = no runnable example (weak);
       D = some example failed (kept in solutions.jsonl, not in sft.jsonl). Python is executed; Java/C++ are never executed here (tier C).
Locked evaluation problems are dropped with --exclude-numbers-file."""
import argparse, ast, json, os, re, subprocess, sys, tempfile, html, hashlib, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_anas_repo import text_of, strip_header, py_sig, java_sig

# ---------------------------------------------------------------- python 2 -> 3
def py2to3(src):
    """Return (py3 source, reason_if_unsafe or None)."""
    if re.search(r"\bcmp\(|\.sort\(cmp|\bbasestring\b|\bunichr\b|\bapply\(|\bfile\(", src): return None, "py2_only_builtin"
    s = src
    s = re.sub(r"\bxrange\(", "range(", s)
    s = re.sub(r"\.iter(items|values|keys)\(\)", r".\1()", s)
    s = re.sub(r"\bizip_longest\b", "zip_longest", s)
    s = re.sub(r"\b(itertools\.)?izip\(", "zip(", s); s = re.sub(r"\b(itertools\.)?imap\(", "map(", s); s = re.sub(r"\b(itertools\.)?ifilter\(", "filter(", s)
    s = s.replace("sys.maxint", "sys.maxsize")
    def fix_import(m):
        names = [n.strip() for n in m.group(2).split(",")]
        names = [{"izip": "zip", "imap": "map", "ifilter": "filter", "izip_longest": "zip_longest"}.get(n, n) for n in names]
        names = [n for n in names if n not in ("zip", "map", "filter")]
        return "from %s import %s" % (m.group(1), ", ".join(names)) if names else ""
    s = re.sub(r"^from (itertools) import ([^\n(]+)$", fix_import, s, flags=re.M)
    s = re.sub(r"^class (\w+)\(object\):", r"class \1:", s, flags=re.M)
    if re.search(r"\breduce\(", s) and not re.search(r"import .*\breduce\b", s): s = "from functools import reduce\n" + s
    try: tree = ast.parse(s)
    except SyntaxError: return None, "syntax_error_py3"
    has_future_div = "from __future__ import division" in s
    for n in ast.walk(tree):
        if isinstance(n, (ast.BinOp, ast.AugAssign)) and isinstance(n.op, ast.Div) and not has_future_div: return None, "py2_division"
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Call):
            f = n.value.func
            if (isinstance(f, ast.Name) and f.id in ("zip", "map", "filter")) or (isinstance(f, ast.Attribute) and f.attr in ("keys", "values", "items")): return None, "py2_list_view_indexing"
    return s, None

def annotate_signature(code, method, sig_line):
    """Replace the `def method(self, a, b):` line by the typed LeetCode signature when parameter names agree."""
    m = re.search(r"^(\s*)def %s\(([^)]*)\)\s*:" % re.escape(method), code, flags=re.M)
    if not m or not sig_line: return code
    try: want = ast.parse(sig_line.strip().rstrip(":") + ":\n    pass").body[0].args
    except SyntaxError: return code
    have = [x.strip().split("=")[0].strip() for x in m.group(2).split(",") if x.strip()]
    if have != [a.arg for a in want.args]: return code
    return code[:m.start()] + m.group(1) + sig_line.strip() + code[m.end():]

def typing_import(code):
    need = [n for n in ("List", "Optional", "Dict", "Set", "Tuple", "Deque") if re.search(r"\b%s\[" % n, code)]
    return ("from typing import %s\n" % ", ".join(need)) if need and not re.search(r"^from typing import", code, flags=re.M) else ""

def tidy_docstring(code):
    return re.sub(r'\n[ ]+"""\n[ ]+:type[^\n]*(?:\n[ ]+:[^\n]*)*\n[ ]+"""', "", code)

# ---------------------------------------------------------------- kamyu python
TIME_RE = re.compile(r"#\s*Time:\s*(.+?)\s*$"); SPACE_RE = re.compile(r"#\s*Space:\s*(.+?)\s*$")

def header_above(lines, lineno, comment="#"):
    """contiguous comment lines directly above (1-based) lineno; returns (time, space, other_comments)."""
    i = lineno - 2; block = []
    while i >= 0 and (lines[i].strip().startswith(comment) or not lines[i].strip()):
        if lines[i].strip(): block.append(lines[i].strip())
        elif block: break
        i -= 1
    t = sp = None; other = []
    pat_t = re.compile(re.escape(comment) + r"\s*Time:\s*(.+?)\s*$"); pat_s = re.compile(re.escape(comment) + r"\s*Space:\s*(.+?)\s*$")
    for c in reversed(block):
        if pat_t.match(c): t = pat_t.match(c).group(1)
        elif pat_s.match(c): sp = pat_s.match(c).group(1)
        else: other.append(c.lstrip("# /").strip())
    return t, sp, other

def clean_cx(x):
    if not x or "ctor" in x or ":" in x: return None
    x = re.sub(r"\s+", " ", x).strip()
    return x if re.match(r"^O\(.*\)$", x) else None

def kamyu_python(path, sig_py, method_hint):
    src = open(path, encoding="utf-8", errors="replace").read()
    new, why = py2to3(src)
    if new is None: return [], why
    tree = ast.parse(new); lines = new.split("\n")
    prelude, classes = [], []
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name.startswith("Solution"): classes.append(n)
        else: prelude.append("\n".join(lines[n.lineno - 1:n.end_lineno]))
    pre = "\n".join(prelude).strip()
    out = []
    for c in classes:
        t, sp, other = header_above(lines, c.lineno)
        funcs = [b for b in c.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))]
        main = next((f for f in funcs if f.name == method_hint), None) or next((f for f in funcs if not f.name.startswith("__")), None)
        if main is None: continue
        keep = {main.name}; changed = True
        while changed:
            changed = False
            for f in funcs:
                if f.name in keep:
                    for a in ast.walk(f):
                        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "self" and a.attr not in keep and any(g.name == a.attr for g in funcs):
                            keep.add(a.attr); changed = True
        segs = ["\n".join(lines[b.lineno - 1:b.end_lineno]) for b in c.body
                if not isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) or b.name in keep or b.name == "__init__"]
        body = "class Solution:\n" + "\n\n".join(segs) + "\n"
        body = tidy_docstring(body)
        body = annotate_signature(body, main.name, (sig_py or "").split("\n")[-1])
        code = (typing_import(body + pre) + (pre + "\n\n" if pre else "") + body)
        vname = c.name[len("Solution"):].strip("_") or "main"
        out.append({"variant": vname, "code": code, "time_complexity": clean_cx(t), "space_complexity": clean_cx(sp), "notes_in_source": other[:3],
                    "tle": "tle" in vname.lower(), "method": main.name})
    return out, None

# ---------------------------------------------------------------- kamyu c++
def kamyu_cpp(path):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n"); out = []; first = None
    i = 0
    while i < len(lines):
        m = re.match(r"^(class|struct) (Solution\w*)\b", lines[i])
        if not m: i += 1; continue
        if first is None: first = i
        depth = 0; j = i; opened = False
        while j < len(lines):
            depth += lines[j].count("{") - lines[j].count("}"); opened = opened or "{" in lines[j]
            if opened and depth <= 0: break
            j += 1
        t, sp, _ = header_above(lines, i + 1, "//")
        body = "\n".join(lines[i:j + 1]); body = re.sub(r"^(class|struct) Solution\w*", r"\1 Solution", body, count=1)
        out.append({"variant": (m.group(2)[len("Solution"):].strip("_") or "main"), "code": body.rstrip() + "\n", "time_complexity": clean_cx(t), "space_complexity": clean_cx(sp),
                    "tle": "tle" in m.group(2).lower(), "ln": i})
        i = j + 1
    pre = "\n".join(l for l in lines[:first] if l.strip() and not l.strip().startswith("//")) if first is not None else ""
    for o in out: o["code"] = (pre + "\n\n" if pre else "") + o["code"]
    return out

# ---------------------------------------------------------------- topics from kamyu md
def topics_by_number(kam):
    ignore = {"Solutions", "Algorithms", "Database", "Shell", "Reference", "SQL", "Shell Script", "Concurrency"}
    top = {}
    for fn in ("0001-1000.md", "1001-2000.md", "2001-3000.md"):
        sec = None
        for l in open(os.path.join(kam, fn), encoding="utf-8", errors="replace"):
            if l.startswith("## "): sec = l[3:].strip()
            m = re.match(r"^\s*(\d{4})\s*\|", l)
            if m and sec and sec not in ignore: top.setdefault(int(m.group(1)), []).append(sec)
    return top

# ---------------------------------------------------------------- statement examples
def parse_examples(statement):
    res = []
    for m in re.finditer(r"Input:\s*(.*?)\n\s*Output:\s*(.*?)(?=\n\s*\n|\nExplanation:|\Z)", statement, flags=re.S):
        inp, outp = m.group(1).strip(), m.group(2).strip()
        masked = re.sub(r'"(?:[^"\\]|\\.)*"', lambda q: "x" * len(q.group(0)), inp)
        idx = [(x.start(), x.end(), x.group(1)) for x in re.finditer(r"(?:(?<=^)|(?<=,\s)|(?<=\s))(\w+)\s*=\s*", masked)]
        # keep only names at top level: those whose start follows start or ", "
        pos = [t for t in idx if t[0] == 0 or inp[:t[0]].rstrip().endswith(",")]
        if not pos: continue
        args = {}
        try:
            for k, (s, e, name) in enumerate(pos):
                end = pos[k + 1][0] if k + 1 < len(pos) else len(inp)
                args[name] = lit(inp[e:end].strip().rstrip(",").strip())
            exp = lit(outp)
        except Exception: continue
        res.append((args, exp))
    return res

def lit(s):
    s = re.sub(r"\btrue\b", "True", s); s = re.sub(r"\bfalse\b", "False", s); s = re.sub(r"\bnull\b", "None", s)
    return ast.literal_eval(s)

HARNESS = r'''
import sys, json, signal, math, collections, heapq, bisect, itertools, functools, string, re, random, operator, copy
from typing import *
from collections import *
from functools import *
from itertools import *
from heapq import *
from bisect import *
from math import *
sys.setrecursionlimit(20000)
try:
    import resource; resource.setrlimit(resource.RLIMIT_AS, (3 << 30, 3 << 30))
except Exception: pass
def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try: return abs(a - b) <= 1e-4 * max(1, abs(b))
        except Exception: return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)): return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b
def canon(x):
    if isinstance(x, (list, tuple)):
        try: return sorted((canon(i) for i in x), key=lambda v: json.dumps(v, sort_keys=True, default=str))
        except Exception: return x
    return x
def onealarm(*a): raise TimeoutError()
signal.signal(signal.SIGALRM, onealarm)
jobs = json.load(open(sys.argv[1])); res = []
for j in jobs:
    ok = tot = unord = 0; firsterr = None
    try:
        signal.alarm(8)
        g = dict(globals()); g["__name__"] = "sol"
        exec(j["code"], g)
        S = g["Solution"]()
        for args, exp in j["examples"]:
            tot += 1
            signal.alarm(8)
            try:
                r = getattr(S, j["method"])(*copy.deepcopy(list(args.values())))
            except TimeoutError: raise
            except Exception as e:
                firsterr = firsterr or (type(e).__name__ + ": " + str(e)[:80]); continue
            if close(r, exp): ok += 1
            elif close(canon(r), canon(exp)): unord += 1
        signal.alarm(0)
    except BaseException as e:
        signal.alarm(0); res.append({"id": j["id"], "total": tot, "passed": ok, "unordered": unord, "error": type(e).__name__}); continue
    res.append({"id": j["id"], "total": tot, "passed": ok, "unordered": unord, "firsterr": firsterr})
json.dump(res, open(sys.argv[2], "w"))
'''

def run_examples(jobs, workers=6, chunk=40):
    import concurrent.futures as cf
    d = tempfile.mkdtemp(prefix="lcrun"); hp = os.path.join(d, "h.py"); open(hp, "w").write(HARNESS)
    def one(k, part):
        jp, rp = os.path.join(d, "j%d.json" % k), os.path.join(d, "r%d.json" % k); json.dump(part, open(jp, "w"))
        try: subprocess.run([sys.executable, "-I", hp, jp, rp], cwd=d, timeout=40 * len(part) + 60, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired: pass
        return json.load(open(rp)) if os.path.exists(rp) else []
    parts = [jobs[i:i + chunk] for i in range(0, len(jobs), chunk)]
    out = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for k, r in enumerate(ex.map(lambda kp: one(*kp), enumerate(parts))):
            for x in r: out[x["id"]] = x
    return out

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--anas", required=True); ap.add_argument("--kamyu", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--exclude-numbers-file"); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--no-run", action="store_true"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    excl = {int(x) for x in open(a.exclude_numbers_file).read().split() if x.strip().isdigit()} if a.exclude_numbers_file else set()
    topics = topics_by_number(a.kamyu); rep = {"dropped_py2": {}, "excluded_locked": 0}
    problems, sols = {}, []
    root = os.path.join(a.anas, "scripts", "algorithms")
    for dp, _, fs in sorted(os.walk(root)):
        if "info.json" not in fs: continue
        info = json.load(open(os.path.join(dp, "info.json"))); num = int(info["id"])
        if info.get("premium") or "README.md" not in fs: continue
        if num in excl: rep["excluded_locked"] += 1; continue
        name = info["name"]; stem = os.path.join(dp, name)
        stm = text_of(open(os.path.join(dp, "README.md"), encoding="utf-8", errors="replace").read()); stm = re.sub(r"^\s*\d+\.\s*" + re.escape(name) + r"\s*\n", "", stm).strip()
        slug = info["url"].rstrip("/").split("/")[-1]
        refs = {}
        for lang, ext in (("python3", ".py"), ("java", ".java")):
            if os.path.exists(stem + ext): refs[lang] = strip_header(open(stem + ext, encoding="utf-8", errors="replace").read())
        psig = py_sig(refs.get("python3", "")); jsig = java_sig(refs.get("java", ""))
        kpy = os.path.join(a.kamyu, "Python", slug + ".py"); kcpp = os.path.join(a.kamyu, "C++", slug + ".cpp")
        method = None
        if psig:
            mm = re.search(r"def (\w+)\(", psig); method = mm.group(1) if mm else None
        p = {"number": num, "title": name, "slug": slug, "difficulty": info["difficulty"].capitalize(), "statement": stm, "python_signature": psig, "java_signature": jsig,
             "topics": sorted(set(topics.get(num, [])))}
        problems[num] = p
        def add(lang, source, code, variant, t=None, s=None, tle=False, method=None):
            sols.append({"number": num, "title": name, "slug": slug, "language": lang, "source": source, "variant": variant, "code": code,
                         "time_complexity": t, "space_complexity": s, "complexity_evidence": "author_label" if (t or s) else None,
                         "expected_to_pass_time_limit": not tle, "method": method})
        if os.path.exists(kpy):
            res, why = kamyu_python(kpy, psig, method)
            if why: rep["dropped_py2"][why] = rep["dropped_py2"].get(why, 0) + 1
            for r in res: add("python3", "kamyu104", r["code"], r["variant"], r["time_complexity"], r["space_complexity"], r["tle"], r["method"])
        if os.path.exists(kcpp):
            for r in kamyu_cpp(kcpp): add("cpp", "kamyu104", r["code"], r["variant"], r["time_complexity"], r["space_complexity"], r["tle"])
        for lang, c in refs.items():
            if lang == "python3":
                c = tidy_docstring(c); c = typing_import(c) + c
            add(lang, "anas", c, "reference", method=method if lang == "python3" else None)
        if a.limit and len(problems) >= a.limit: break
    # exact duplicate removal (normalised) within a problem+language
    seen, uniq = set(), []
    for s in sols:
        k = (s["number"], s["language"], hashlib.sha1(re.sub(r"\s+", "", re.sub(r"#.*|//.*", "", s["code"])).encode()).hexdigest())
        if k in seen: continue
        seen.add(k); uniq.append(s)
    rep["duplicates_removed"] = len(sols) - len(uniq); sols = uniq
    # examples
    jobs = []
    for i, s in enumerate(sols):
        s["id"] = i
        if s["language"] == "python3" and s["method"]:
            sig = problems[s["number"]]["python_signature"] or ""
            if not re.search(r"ListNode|TreeNode|Node\b|-> None|:\s*'?Node", sig):
                ex = parse_examples(problems[s["number"]]["statement"])
                if ex: jobs.append({"id": i, "code": s["code"], "method": s["method"], "examples": ex})
    got = {} if a.no_run else run_examples(jobs, a.workers)
    rep["python_with_examples"] = len(jobs)
    for s in sols:
        r = got.get(s["id"]); s["examples"] = {"total": r["total"], "passed": r["passed"], "unordered": r["unordered"], "error": r.get("error"), "firsterr": r.get("firsterr")} if r else None
        if r and r["total"] > 0:
            full = r["passed"] + r["unordered"] == r["total"] and r["passed"] + r["unordered"] > 0 and not r.get("error")
            s["tier"] = ("A" if (s["complexity_evidence"] and full) else "B") if full else "D"
        else: s["tier"] = "C"
        if s["tier"] == "C" and r is None and not a.no_run and s["language"] == "python3" and s["method"] and False: pass
        del s["id"]
    # a problem whose every python solution fails is most likely a mis-parsed statement example, not 10 wrong solutions
    bad = {}
    for s in sols:
        if s["language"] == "python3" and s["examples"]: bad.setdefault(s["number"], []).append(s["tier"] == "D")
    for s in sols:
        if s["tier"] == "D" and all(bad.get(s["number"], [False])) and len(bad[s["number"]]) >= 2: s["tier"] = "C"; s["examples"]["unreliable"] = True
    with open(os.path.join(a.out, "problems.jsonl"), "w") as f:
        for p in problems.values(): f.write(json.dumps(p) + "\n")
    with open(os.path.join(a.out, "solutions.jsonl"), "w") as f:
        for s in sols: f.write(json.dumps(s) + "\n")
    n_sft = 0
    with open(os.path.join(a.out, "sft.jsonl"), "w") as f:
        for s in sols:
            if s["tier"] == "D": continue
            p = problems[s["number"]]; lang_name = {"python3": "Python 3", "java": "Java", "cpp": "C++"}[s["language"]]
            sig = p["python_signature"] if s["language"] == "python3" else p["java_signature"] if s["language"] == "java" else None
            user = "Solve this problem in %s.\n\n%s\n\n%s" % (lang_name, p["title"] + " (" + p["difficulty"] + ")", p["statement"]) + ("\n\nUse this signature:\n" + sig if sig else "")
            fence = {"python3": "python", "java": "java", "cpp": "cpp"}[s["language"]]
            asst = "```%s\n%s\n```" % (fence, s["code"].rstrip())
            if not s["expected_to_pass_time_limit"]: asst += "\n\nThis is a straightforward approach that exceeds the time limit on the largest inputs."
            if s["time_complexity"] and s["space_complexity"]: asst += "\n\nTime complexity: %s. Space complexity: %s." % (s["time_complexity"], s["space_complexity"])
            f.write(json.dumps({"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": asst}], "number": s["number"], "language": s["language"], "tier": s["tier"], "source": s["source"]}) + "\n"); n_sft += 1
    from collections import Counter
    rep.update({"problems": len(problems), "solutions": len(sols), "sft": n_sft, "by_language": dict(Counter(s["language"] for s in sols)), "by_tier": dict(Counter(s["tier"] for s in sols)),
                "by_tier_python": dict(Counter(s["tier"] for s in sols if s["language"] == "python3")),
                "labelled": sum(1 for s in sols if s["complexity_evidence"]), "tle_variants": sum(1 for s in sols if not s["expected_to_pass_time_limit"])})
    json.dump(rep, open(os.path.join(a.out, "report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
if __name__ == "__main__": main()
