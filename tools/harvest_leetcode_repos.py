#!/usr/bin/env python3
"""Harvest LeetCode problems with SEVERAL human-written Python and Java solutions, plus complexity analysis, from public GitHub repositories.
This replaces scraping leetcode.com (login walls, bot protection, account/IP risk, fragile): the repositories already contain the same material in plain files.

Sources (cloned shallow + sparse, only the needed files; GitHub only):
  doocs/leetcode           solution/**/README_EN.md : problem statement, "Solution N: <approach>" sections with an explanation that states the time/space
                           complexity, a short "Thinking" note, and a Python3 and a Java tab per approach. One row per (approach, language).
  kamyu104/LeetCode-Solutions   Python/<slug>.py : several solutions per file, each headed by "# Time: O(..)" / "# Space: O(..)" written by the author.
                           Statement comes from doocs (matched by slug). One solution row and one "what is the complexity?" row per solution.
  fishercoder1534/Leetcode src/main/java/.../_N.java : Solution1, Solution2 ... classes (extra Java solutions). Statement from doocs (matched by number).

  python3 tools/harvest_leetcode_repos.py fetch --dest ~/lc_repos
  python3 tools/harvest_leetcode_repos.py build --src ~/lc_repos --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --locked ~/locked_eval_1365.jsonl \\
        --out ~/sft_lc2/lc_repos.jsonl --report ~/sft_lc2/lc_repos_report.json

Safety: problems whose number is in the newfacade/LeetCodeDataset TEST split (the source of the locked LeetCode eval tasks) are excluded by number, and every row also
goes through the locked-task overlap rule of build_sft_corpus. Rows are labelled "unverified_human": written by people and normally accepted by LeetCode, but never run by us.
Output rows are in the SFT format: {"text": "Question: <Q>\\n\\nAnswer:\\n<A>", "prov": {"seed_id", "variant": "direct"}, "meta": {...}}."""
import argparse, ast, hashlib, html, json, os, re, subprocess, sys, time, warnings
from html.parser import HTMLParser
warnings.filterwarnings("ignore", category=SyntaxWarning)   # ast.parse of old code with bad escapes

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

REPOS = {   # name -> (url, sparse patterns)
    "doocs": ("https://github.com/doocs/leetcode.git", ["/solution/**/README_EN.md"]),
    "kamyu": ("https://github.com/kamyu104/LeetCode-Solutions.git", ["/Python/*.py"]),
    "fisher": ("https://github.com/fishercoder1534/Leetcode.git", ["/src/main/java/com/fishercoder/solutions/**/_*.java"]),
    "walk": ("https://github.com/walkccc/LeetCode.git", ["/solutions/**/*.py", "/solutions/**/*.java"]),   # N. Title/N.py, N-2.py ... + N.java
}
SEP = "\n\nAnswer:\n"


# ----------------------------------------------------------------------------------------------------------------------------- fetch
def fetch(dest, only=None):
    os.makedirs(dest, exist_ok=True)
    for name, (url, pats) in REPOS.items():
        if only and name not in only: continue
        d = os.path.join(dest, name)
        if not os.path.isdir(os.path.join(d, ".git")):
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", url, d], check=True)
        subprocess.run(["git", "-C", d, "sparse-checkout", "set", "--no-cone", *pats], check=True)
        subprocess.run(["git", "-C", d, "checkout"], check=True)
        n = sum(len(fs) for _, _, fs in os.walk(d) if ".git" not in _)
        print(f"{name}: ok, {n} files checked out", flush=True)


# ----------------------------------------------------------------------------------------------------------------------------- text helpers
class _Html2Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("p", "div", "br", "ul", "ol", "pre", "table", "tr"): self.out.append("\n")
        elif tag == "li": self.out.append("\n- ")
        elif tag == "sup": self.out.append("^")
        elif tag in ("script", "style", "img"): self.skip += tag != "img"
    def handle_endtag(self, tag):
        if tag in ("p", "div", "pre", "ul", "ol", "table"): self.out.append("\n")
        elif tag in ("script", "style"): self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip: self.out.append(data)


def html_to_text(s):
    p = _Html2Text(); p.feed(s); p.close()
    t = "".join(p.out).replace("\xa0", " ").replace("\r", "")
    t = re.sub(r"[ \t]+\n", "\n", t); t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def norm_code(code):
    return re.sub(r"\s+", " ", code).strip()


# ----------------------------------------------------------------------------------------------------------------------------- doocs
TITLE = re.compile(r"^# \[(\d+)\. (.+?)\]\(https://leetcode\.(?:com|cn)/problems/([^/)\s]+)", re.M)
FRONT = re.compile(r"\A---\n(.*?)\n---", re.S)


def parse_doocs(md):
    """README_EN.md text -> dict(number, title, slug, difficulty, description, solutions=[{title, thinking, explanation, code:{python, java}}]) or None."""
    m = TITLE.search(md)
    if not m: return None
    num, title, slug = int(m.group(1)), m.group(2).strip(), m.group(3)
    fm = FRONT.match(md); diff = None; tags = []
    if fm:
        d = re.search(r"^difficulty:\s*(\w+)", fm.group(1), re.M); diff = d.group(1) if d else None
        t = re.search(r"^tags:\s*\n((?:\s+- .+\n?)+)", fm.group(1) + "\n", re.M)
        if t: tags = [x.strip() for x in re.findall(r"^\s+- (.+)$", t.group(1), re.M)]
    d = re.search(r"<!-- description:start -->(.*?)<!-- description:end -->", md, re.S)
    desc = html_to_text(d.group(1)) if d else ""
    sols = []
    s = re.search(r"<!-- solution:start -->(.*?)<!-- solution:end -->", md, re.S)
    if s:
        parts = re.split(r"^### (.+)$", s.group(1), flags=re.M)
        for i in range(1, len(parts) - 1, 2):
            head, body = parts[i].strip(), parts[i + 1]
            think = re.search(r"<!-- thinking:start -->(.*?)<!-- thinking:end -->", body, re.S)
            thinking = ""
            if think:
                lines = [re.sub(r"^>\s?", "", l).rstrip() for l in think.group(1).strip().splitlines()]
                thinking = "\n".join(l for l in lines if l.strip() != "**Thinking**").strip()
                body = body.replace(think.group(0), "")
            tabs = re.search(r"<!-- tabs:start -->(.*?)<!-- tabs:end -->", body, re.S)
            expl = body[:tabs.start()] if tabs else body
            expl = re.sub(r"<!--.*?-->", "", expl, flags=re.S).strip()
            code = {}
            if tabs:
                for h, lang, c in re.findall(r"^#### (.+?)\n+```(\w+)\n(.*?)\n```", tabs.group(1), re.S | re.M):
                    k = {"python3": "python", "python": "python", "java": "java"}.get(h.strip().lower())
                    if k and k not in code: code[k] = c.strip("\n")
            if code:
                sols.append({"title": re.sub(r"^Solution\s*\d*\s*:?\s*", "", head).strip() or head, "thinking": thinking, "explanation": expl, "code": code})
    return {"number": num, "title": title, "slug": slug, "difficulty": diff, "tags": tags, "description": desc, "solutions": sols}


# ----------------------------------------------------------------------------------------------------------------------------- kamyu (python with Time/Space headers)
HDR = re.compile(r"^# Time:\s*(.+?)\s*\n# Space:\s*(.+?)\s*\n", re.M)
COMPLEXITY = re.compile(r"^O\([^#]*\)$")
PY2 = re.compile(r"\bxrange\b|\biteritems\b|\bitervalues\b|\braw_input\b|^\s*print\s+[^(\s]|\bunicode\(|\blong\(", re.M)


def parse_kamyu(src):
    """-> [(time, space, code)] for each header-delimited solution that parses under Python 3."""
    hs = list(HDR.finditer(src)); out = []
    for i, h in enumerate(hs):
        end = hs[i + 1].start() if i + 1 < len(hs) else len(src)
        body = src[h.end():end].strip("\n")
        if not body.strip() or PY2.search(body): continue
        try: ast.parse(body)
        except (SyntaxError, ValueError, MemoryError, RecursionError): continue
        t, sp = h.group(1).strip(), h.group(2).strip()
        out.append((t if COMPLEXITY.match(t) else None, sp if COMPLEXITY.match(sp) else None, body))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- fishercoder (java, SolutionN classes)
SOL_CLASS = re.compile(r"public static class Solution\d*\s*(?:extends \w+\s*)?\{")


def _strip_noise(s):
    s = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), s, flags=re.S)
    s = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), s)
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\'', lambda m: " " * len(m.group(0)), s)


def parse_fisher(src):
    """-> [(imports, class_source)] for each `public static class SolutionN {...}` (renamed to `class Solution`)."""
    imports = "\n".join(re.findall(r"^import [\w.*]+;$", src, re.M))
    clean = _strip_noise(src); out = []
    for m in SOL_CLASS.finditer(clean):
        depth, i = 0, m.end() - 1
        while i < len(clean):
            if clean[i] == "{": depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0: break
            i += 1
        if depth != 0: continue
        body = src[m.start():i + 1]
        body = re.sub(r"^public static class Solution\d*", "class Solution", body)
        body = re.sub(r"^\s{4}", "", body, flags=re.M)
        out.append((imports, body))
    return out



# ----------------------------------------------------------------------------------------------------------------------------- quality gates
import builtins
LC_PROVIDED = {"List", "Optional", "Dict", "Set", "Tuple", "Deque", "ListNode", "TreeNode", "Node", "Solution", "self", "cls", "Iterator"}   # names the LeetCode judge injects
PY2_API = re.compile(r"\.(?:iterkeys|itervalues|iteritems|has_key)\(|\.(?:keys|values|items)\(\)\[|\bmap\([^)]*\)\[|\bfilter\([^)]*\)\[|\bzip\([^)]*\)\[")
SUBSCRIPT_DIV = re.compile(r"\[[^\]\n]*[^/\s]\s*/\s*[^/=\s][^\]\n]*\]")   # a[i / 2]: float index under Python 3


def python_hazards(code):
    """Why this Python solution would fail under Python 3 (or None): py2 API, float index, or a name that is never defined."""
    if PY2_API.search(code): return "python2_api"
    if SUBSCRIPT_DIV.search(re.sub(r"#.*", "", code)): return "python2_division_index"
    try: tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError): return "python_syntax"
    und = undefined_names(tree)
    return ("undefined_name:" + sorted(und)[0]) if und else None


def undefined_names(tree):
    bound = set(dir(builtins)) | LC_PROVIDED
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): bound.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): bound.add(n.name)
        elif isinstance(n, ast.arg): bound.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name: bound.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names: bound.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, (ast.Global, ast.Nonlocal)): bound.update(n.names)
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound}


STD_MODULES = {"collections", "math", "functools", "itertools", "heapq", "bisect", "string", "random", "operator", "re", "sys"}
STD_NAMES = {}
for _m, _ns in {"collections": "Counter defaultdict deque OrderedDict namedtuple", "functools": "cache lru_cache reduce cmp_to_key partial",
                "itertools": "pairwise accumulate product permutations combinations groupby zip_longest chain", "heapq": "heapify heappush heappop heapreplace heappushpop nlargest nsmallest",
                "bisect": "bisect_left bisect_right insort", "math": "gcd sqrt comb perm floor ceil log2 lcm isqrt inf",
                "sortedcontainers": "SortedList SortedDict SortedSet", "string": "ascii_lowercase ascii_uppercase ascii_letters digits"}.items():
    for _n in _ns.split(): STD_NAMES[_n] = _m


def add_std_imports(code):
    """LeetCode's judge pre-imports the usual stdlib names; make the saved snippet self-contained. Returns (code, changed)."""
    try: und = undefined_names(ast.parse(code))
    except (SyntaxError, ValueError, MemoryError, RecursionError): return code, False
    lines = [f"import {n}" for n in sorted(und & STD_MODULES)] + [f"from {STD_NAMES[n]} import {n}" for n in sorted(und) if n in STD_NAMES]
    return (("\n".join(lines) + "\n\n" + code, True) if lines else (code, False))


def file_imports(src):
    """Top-level import statements of a python file -> [(bound_names, source_line)]."""
    out = []
    try: tree = ast.parse(src)
    except (SyntaxError, ValueError, MemoryError, RecursionError): return out
    lines = src.splitlines()
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)) and n.end_lineno == n.lineno:
            out.append(({(al.asname or al.name).split(".")[0] for al in n.names}, lines[n.lineno - 1].strip()))
    return out


def with_imports(body, imports):
    names = {n.id for n in ast.walk(ast.parse(body)) if isinstance(n, ast.Name)} | {n.value.id for n in ast.walk(ast.parse(body)) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    need = [line for bound, line in imports if bound & names]
    return ("\n".join(need) + "\n\n" if need else "") + body


def last_code(ans):
    b = re.findall(r"```(\w+)\n(.*?)```", ans, re.S)
    return b[-1][1] if b else ""

# ----------------------------------------------------------------------------------------------------------------------------- rows
def question(p, lang):
    head = f"{p['number']}. {p['title']}" + (f" ({p['difficulty']})" if p.get("difficulty") else "")
    return f"{head}\n\n{p['description']}\n\nSolve this problem in {'Python' if lang == 'python' else 'Java'}."


def topics_line(p):
    return ("Topics: " + ", ".join(p["tags"])) if p.get("tags") else ""


def doocs_answer(sol, lang, thinking=True, topics=""):
    parts = ([topics] if topics else []) + [f"Approach: {sol['title']}"]
    if thinking and sol["thinking"]: parts.append("Idea: " + sol["thinking"])
    if sol["explanation"]: parts.append(sol["explanation"])
    parts.append(f"```{lang}\n{sol['code'][lang].strip()}\n```")
    return "\n\n".join(parts)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f: return f.read()


def iter_candidates(src, a):
    """Yield (problem_number, kind, language, source, key, question, answer, extra) for every row before filtering."""
    probs, by_slug = {}, {}
    droot = os.path.join(src, "doocs")
    for root, _, files in os.walk(droot):
        if ".git" in root.split(os.sep): continue
        if "README_EN.md" in files:
            p = parse_doocs(read(os.path.join(root, "README_EN.md")))
            if p: probs[p["number"]] = p; by_slug[p["slug"]] = p
    print(f"doocs: {len(probs)} problems parsed, {sum(len(p['solutions']) for p in probs.values())} approaches", flush=True)
    for n, p in sorted(probs.items()):
        if not p["description"]: continue
        for si, sol in enumerate(p["solutions"], 1):
            for lang in ("python", "java"):
                if lang in sol["code"]:
                    yield n, "solution", lang, "lc_doocs", f"{n}:doocs:{si}:{lang}", question(p, lang), doocs_answer(sol, lang, not a.no_thinking, "" if a.no_topics else topics_line(p)), {"approach": sol["title"], "difficulty": p["difficulty"], "tags": p.get("tags", [])}
    kdir = os.path.join(src, "kamyu", "Python")
    if os.path.isdir(kdir):
        for fn in sorted(os.listdir(kdir)):
            slug = fn[:-3] if fn.endswith(".py") else None
            p = by_slug.get(slug)
            if not p or not p["description"]: continue
            ksrc = read(os.path.join(kdir, fn)); kimp = file_imports(ksrc)
            for si, (t, sp, code) in enumerate(parse_kamyu(ksrc), 1):
                code = with_imports(code, kimp)
                cx = f"Time complexity: {t}. Space complexity: {sp}." if t and sp else None
                yield p["number"], "solution", "python", "lc_kamyu", f"{p['number']}:kamyu:{si}", question(p, "python"), ("" if a.no_topics or not topics_line(p) else topics_line(p) + "\n\n") + ((cx + "\n\n") if cx else "") + f"```python\n{code}\n```", {"has_complexity": bool(cx), "difficulty": p["difficulty"], "tags": p.get("tags", [])}
                if cx:
                    yield p["number"], "complexity", "python", "lc_kamyu", f"{p['number']}:kamyu:{si}:cx", f"What are the time and space complexity of this Python solution?\n\n```python\n{code}\n```", cx, {"difficulty": p["difficulty"], "tags": p.get("tags", [])}
    fdir = os.path.join(src, "fisher")
    byn = probs
    for root, _, files in os.walk(fdir):
        if ".git" in root.split(os.sep): continue
        for fn in sorted(files):
            m = re.fullmatch(r"_(\d+)\.java", fn)
            p = byn.get(int(m.group(1))) if m else None
            if not p or not p["description"]: continue
            for si, (imp, body) in enumerate(parse_fisher(read(os.path.join(root, fn))), 1):
                imp = "\n".join(l for l in imp.splitlines() if not re.match(r"import com\.fishercoder\.common\.classes\.", l))   # TreeNode/ListNode/Node come from the judge
                if "com.fishercoder" in imp: continue   # needs the author's own helper classes
                code = (imp + "\n\n" if imp else "") + body
                yield p["number"], "solution", "java", "lc_fisher", f"{p['number']}:fisher:{si}", question(p, "java"), ("" if a.no_topics or not topics_line(p) else topics_line(p) + "\n\n") + f"```java\n{code.strip()}\n```", {"difficulty": p["difficulty"], "tags": p.get("tags", [])}
    wdir = os.path.join(src, "walk", "solutions")
    if os.path.isdir(wdir):
        for d in sorted(os.listdir(wdir)):
            m = re.match(r"(\d+)\. ", d); p = probs.get(int(m.group(1))) if m else None
            if not p or not p["description"]: continue
            for fn in sorted(os.listdir(os.path.join(wdir, d))):
                fm = re.fullmatch(r"\d+(?:-(\d+))?\.(py|java)", fn)
                if not fm: continue
                lang = "python" if fm.group(2) == "py" else "java"; code = read(os.path.join(wdir, d, fn)).strip()
                if len(code) < 40: continue
                yield p["number"], "solution", lang, "lc_walk", f"{p['number']}:walk:{fm.group(1) or 1}:{lang}", question(p, lang), ("" if a.no_topics or not topics_line(p) else topics_line(p) + "\n\n") + f"```{lang}\n{code}\n```", {"difficulty": p["difficulty"], "tags": p.get("tags", [])}


def build(src, a, count, locked, specials, excluded):
    import build_sft_corpus as B
    import hf_sft_adapter as A
    rep = {"read": 0, "kept": 0, "tokens": 0, "dropped": {}, "by_source": {}, "by_kind": {}}
    seen_code, rows, cover = set(), [], {}
    def drop(w): rep["dropped"][w] = rep["dropped"].get(w, 0) + 1
    for n, kind, lang, source, key, q, ans, extra in iter_candidates(src, a):
        rep["read"] += 1
        if n in excluded: drop("test_split_problem"); continue
        if any(x in q or x in ans for x in specials): drop("contains_special_token_string"); continue
        if SEP in q or SEP in ans: drop("contains_qa_separator"); continue
        if count(q) + count(ans) + 16 > a.max_tokens: drop("too_long"); continue
        if kind == "solution" and len(last_code(ans).strip()) < 30: drop("empty_code"); continue
        if lang == "python" and kind == "complexity":
            why = python_hazards(last_code(q))
            if why: drop(why.split(":")[0]); continue
        if lang == "python" and kind == "solution":
            old = last_code(ans); fixed, ch = add_std_imports(old.rstrip("\n"))
            if ch: ans = ans[::-1].replace(old[::-1], (fixed + "\n")[::-1], 1)[::-1]
            why = python_hazards(last_code(ans))
            if why: drop(why.split(":")[0]); continue
        if kind == "solution":
            h = hashlib.sha256((str(n) + lang + norm_code(ans.split("```" + lang, 1)[-1])).encode()).hexdigest()
            if h in seen_code: drop("duplicate_solution"); continue
            seen_code.add(h)
        why = B.overlap_reason(q, ans, locked)
        if why: drop(why); continue
        rows.append({"text": f"Question: {q}{SEP}{ans}", "prov": {"seed_id": "lc:" + key, "variant": "direct"},
                     "meta": {"source_dataset": source, "language": lang, "label": "unverified_human", "kind": kind, "problem_number": n, **extra}})
        rep["kept"] += 1; rep["tokens"] += count(q) + count(ans)
        rep["by_source"][source] = rep["by_source"].get(source, 0) + 1; rep["by_kind"][kind] = rep["by_kind"].get(kind, 0) + 1
        if kind == "solution":
            c = cover.setdefault(n, {"python": 0, "java": 0}); c[lang] += 1
    if a.max_per_problem_lang:   # round-robin across sources so one repo's many variants cannot crowd out the others
        groups = {}
        for r in rows:
            if r["meta"]["kind"] == "solution": groups.setdefault((r["meta"]["problem_number"], r["meta"]["language"]), {}).setdefault(r["meta"]["source_dataset"], []).append(r)
        keep = set(); cover = {}
        for (n, lang), bysrc in groups.items():
            queues = [bysrc[k] for k in sorted(bysrc)]; chosen = []
            while len(chosen) < a.max_per_problem_lang and any(queues):
                for qd in queues:
                    if qd and len(chosen) < a.max_per_problem_lang: chosen.append(qd.pop(0))
            keep.update(id(r) for r in chosen); cover.setdefault(n, {"python": 0, "java": 0})[lang] += len(chosen)
        before = len(rows); rows = [r for r in rows if r["meta"]["kind"] != "solution" or id(r) in keep]
        rep["capped_out"] = before - len(rows); rep["kept"] = len(rows)
        rep["by_source"] = {}; rep["by_kind"] = {}
        for r in rows:
            m = r["meta"]; rep["by_source"][m["source_dataset"]] = rep["by_source"].get(m["source_dataset"], 0) + 1; rep["by_kind"][m["kind"]] = rep["by_kind"].get(m["kind"], 0) + 1
        rep["tokens"] = sum(count(r["text"]) for r in rows)
    rep["problems_with_rows"] = len(cover)
    rep["problems_with_2plus_python"] = sum(1 for c in cover.values() if c["python"] >= 2)
    rep["problems_with_2plus_java"] = sum(1 for c in cover.values() if c["java"] >= 2)
    rep["problems_with_2plus_both"] = sum(1 for c in cover.values() if c["python"] >= 2 and c["java"] >= 2)
    return rows, rep


def test_split_numbers():
    from datasets import load_dataset
    ds = load_dataset("newfacade/LeetCodeDataset", split="test")
    return {int(x) for x in ds["question_id"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("--dest", required=True); f.add_argument("--only", help="comma list of doocs,kamyu,fisher,walk")
    b = sub.add_parser("build"); b.add_argument("--src", required=True); b.add_argument("--out", required=True); b.add_argument("--report", required=True)
    b.add_argument("--tokenizer"); b.add_argument("--locked"); b.add_argument("--max-tokens", type=int, default=1900); b.add_argument("--no-thinking", action="store_true")
    b.add_argument("--no-topics", action="store_true", help="do not put the 'Topics: Array, Hash Table' (algorithm-pattern tags) line at the start of doocs/walk answers")
    b.add_argument("--max-per-problem-lang", type=int, default=6, help="keep at most this many solutions per problem and language, round-robin across sources (0 = no cap)")
    b.add_argument("--exclude-numbers-file", help="text file with one LeetCode problem number per line to exclude (default: the newfacade test split, read with `datasets`)")
    b.add_argument("--allow-no-exclude", action="store_true", help="only for tests: do not exclude test-split problems")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(os.path.expanduser(a.dest), set(a.only.split(",")) if a.only else None); return
    import build_sft_corpus as B
    import hf_sft_adapter as A
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(os.path.expanduser(a.tokenizer)); count = lambda s: len(tk.encode(s).ids); specials = A.special_strings(os.path.expanduser(a.tokenizer))
    else:
        print("NOTE: no --tokenizer: tokens estimated as chars/3"); count = lambda s: len(s) // 3 + 1; specials = A.DEFAULT_SPECIALS
    locked = B.load_locked(a.locked) if a.locked else None
    if not locked: print("NOTE: no --locked: overlap with the locked tasks NOT checked. Do not train on this file.")
    if a.exclude_numbers_file: excluded = {int(l) for l in open(os.path.expanduser(a.exclude_numbers_file)) if l.strip()}
    elif a.allow_no_exclude: excluded = set()
    else: excluded = test_split_numbers()
    print(f"excluding {len(excluded)} test-split problem numbers", flush=True)
    t0 = time.time()
    rows, rep = build(os.path.expanduser(a.src), a, count, locked, specials, excluded)
    rep.update(seconds=round(time.time() - t0, 1), excluded_numbers=len(excluded), locked_checked=bool(locked))
    os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(a.out))), exist_ok=True)
    with open(os.path.expanduser(a.out), "w", encoding="utf-8") as fo:
        for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        fo.flush(); os.fsync(fo.fileno())
    json.dump(rep, open(os.path.expanduser(a.report), "w"), indent=1); print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
