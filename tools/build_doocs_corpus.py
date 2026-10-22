#!/usr/bin/env python3
"""Corpus from github.com/doocs/leetcode (CC BY-SA 4.0 - recorded in each record's `license`; private experiment) and, optionally,
the `hjmao` branch of github.com/huajianmao/leetcode (Java solutions, one class per problem).
doocs gives, per problem and per "Solution N: <title>": a written explanation (+ an optional 'Thinking' block), complexity stated in prose,
and code in many languages. Output (--out): problems.jsonl, solutions.jsonl, sft.jsonl, report.json (same tier rules as build_leetcode_corpus.py).
  python3 tools/build_doocs_corpus.py --doocs doocs-leetcode --hjmao hj-leetcode --out out --exclude-numbers-file locked/locked_leetcode_numbers.txt"""
import argparse, ast, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_anas_repo import text_of
import build_leetcode_corpus as B

LANG = {"python3": "python3", "python": "python3", "java": "java", "c++": "cpp", "go": "go", "typescript": "typescript", "javascript": "javascript",
        "rust": "rust", "c#": "csharp", "php": "php", "c": "c", "kotlin": "kotlin", "swift": "swift", "ruby": "ruby", "scala": "scala"}

def latex_plain(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s); s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\$\$\s*(.*?)\s*\$\$", lambda m: "\n" + m.group(1) + "\n", s, flags=re.S)
    s = re.sub(r"\$([^$\n]+)\$", r"\1", s)
    for a, b in ((r"\\times", "*"), (r"\\cdot", "*"), (r"\\leq?", "<="), (r"\\geq?", ">="), (r"\\neq", "!="), (r"\\ldots|\\cdots|\\dots", "..."),
                 (r"\\log", "log"), (r"\\max", "max"), (r"\\min", "min"), (r"\\sum", "sum"), (r"\\sqrt", "sqrt"), (r"\\lfloor", "floor("), (r"\\rfloor", ")"),
                 (r"\\lceil", "ceil("), (r"\\rceil", ")"), (r"\\text\{([^}]*)\}", r"\1"), (r"\\textit\{([^}]*)\}", r"\1"), (r"\\mathrm\{([^}]*)\}", r"\1"),
                 (r"\\operatorname\{([^}]*)\}", r"\1"), (r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)"), (r"\\&", "&"), (r"\\\\", " "), (r"\\,|\;|\\!|\\ ", " "),
                 (r"\^\{([^}]*)\}", r"^\1"), (r"_\{([^}]*)\}", r"_\1"), (r"\\left|\\right", ""), (r"\\in\b", "in"), (r"\\lt\b", "<"), (r"\\gt\b", ">"), (r"\\to\b", "->"),
                 (r"\\oplus", "XOR"), (r"\\&|\\%", "%"), (r"\\begin\{cases\}|\\end\{cases\}|\\begin\{aligned\}|\\end\{aligned\}", ""),
                 (r"\\(?:mod|bmod|pmod)\b", "mod"), (r"\\infty", "infinity"), (r"\\(?:lor)\b", "or"), (r"\\(?:land|wedge)\b", "and"), (r"\\(?:ne|neq)\b", "!="),
                 (r"\\(?:texttt|underline|mathbf|mathcal|boldsymbol|overline)\{([^}]*)\}", r"\1"), (r"\\mid\b", "|"), (r"\\q?quad\b", " ")):
        s = re.sub(a, b, s)
    s = re.sub(r"\\([a-zA-Z]+)", r"\1", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()

def balanced_O(s, start):
    i = s.find("O(", start)
    if i < 0: return None
    d = 0
    for j in range(i + 1, len(s)):
        d += s[j] == "("; d -= s[j] == ")"
        if d == 0: return s[i:j + 1]
    return None

def complexities(text):
    t = sp = None
    m = re.search(r"[Tt]ime complexity[^O]{0,60}", text)
    if m: t = balanced_O(text, m.start())
    m = re.search(r"[Ss]pace complexity[^O]{0,60}", text)
    if m: sp = balanced_O(text, m.start())
    return B.clean_cx(t), B.clean_cx(sp)

def parse_doocs(path, excl):
    d = open(path, encoding="utf-8", errors="replace").read()
    mt = re.search(r"^# \[(\d+)\. (.*?)\]\((.*?)\)", d, flags=re.M)
    if not mt: return None
    num = int(mt.group(1))
    if num in excl or "/solution/" not in path.replace(os.sep, "/") + "/": return None
    fm = re.match(r"---\n(.*?)\n---", d, flags=re.S); fm = fm.group(1) if fm else ""
    diff = re.search(r"difficulty:\s*(\w+)", fm); tags = re.findall(r"^\s+-\s*(.+)$", fm.split("tags:")[-1], flags=re.M) if "tags:" in fm else []
    md = re.search(r"<!-- description:start -->(.*?)<!-- description:end -->", d, flags=re.S)
    prob = {"number": num, "title": mt.group(2), "slug": mt.group(3).rstrip("/").split("/")[-1], "difficulty": (diff.group(1) if diff else "").capitalize(),
            "statement": text_of(md.group(1)) if md else "", "topics": tags}
    sols = []
    body = d.split("## Solutions", 1)[1] if "## Solutions" in d else ""
    parts = re.split(r"^### (Solution \d+[:：].*)$", body, flags=re.M)
    for k in range(1, len(parts), 2):
        title = re.sub(r"^Solution \d+[:：]\s*", "", parts[k]).strip(); chunk = parts[k + 1]
        th = re.search(r"<!-- thinking:start -->(.*?)<!-- thinking:end -->", chunk, flags=re.S)
        thinking = None
        if th:
            thinking = latex_plain("\n".join(re.sub(r"^>\s?", "", l) for l in th.group(1).split("\n")).replace("**Thinking**", "")).strip() or None
            chunk = chunk.replace(th.group(0), "")
        ta = re.search(r"<!-- tabs:start -->(.*?)<!-- tabs:end -->", chunk, flags=re.S)
        pre = chunk.split("<!-- tabs:start -->")[0]; post = chunk.split("<!-- tabs:end -->", 1)[1] if ta else ""
        expl = latex_plain(pre + "\n" + post.split("<!-- solution:end -->")[0])
        expl = re.sub(r"\n#{2,4} [^\n]*$", "", expl).strip()
        t, sp = complexities(expl)
        for lm in re.finditer(r"^#### ([^\n]+)\n+```(\w*)\n(.*?)```", ta.group(1) if ta else "", flags=re.S | re.M):
            lang = LANG.get(lm.group(1).strip().lower())
            if not lang: continue
            sols.append({"number": num, "title": prob["title"], "slug": prob["slug"], "language": lang, "source": "doocs", "variant": "solution%d" % (k // 2 + 1),
                         "approach": title, "explanation": expl, "thinking": thinking, "code": lm.group(3).rstrip() + "\n", "time_complexity": t, "space_complexity": sp,
                         "complexity_evidence": "author_label" if (t or sp) else None, "expected_to_pass_time_limit": True, "license": "CC-BY-SA-4.0"})
    return prob, sols

def hjmao_java(root, slug2num, excl):
    out = []
    for dp, _, fs in os.walk(os.path.join(root, "src", "main", "java", "cn", "hjmao", "leetcode")):
        for f in fs:
            if f != "Solution.java": continue
            s = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
            m = re.search(r"https://leetcode\.com/problems/([\w-]+)", s)
            if not m or m.group(1) not in slug2num or slug2num[m.group(1)] in excl: continue
            s = re.sub(r"^package [^\n]*\n", "", s); s = re.sub(r"/\*\*.*?\*/", "", s, count=1, flags=re.S).strip() + "\n"
            s = s.replace("public class Solution", "class Solution", 1)
            if "class Solution" not in s: continue
            out.append((slug2num[m.group(1)], m.group(1), s))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--doocs", required=True); ap.add_argument("--hjmao"); ap.add_argument("--out", required=True)
    ap.add_argument("--exclude-numbers-file"); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--no-run", action="store_true"); ap.add_argument("--no-java", action="store_true"); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    excl = {int(x) for x in open(a.exclude_numbers_file).read().split() if x.strip().isdigit()} if a.exclude_numbers_file else set()
    problems, sols = {}, []
    for dp, _, fs in sorted(os.walk(os.path.join(a.doocs, "solution"))):
        if "README_EN.md" in fs:
            r = parse_doocs(os.path.join(dp, "README_EN.md"), excl)
            if r: problems[r[0]["number"]] = r[0]; sols += r[1]
    rep = {"doocs_problems": len(problems), "doocs_solutions": len(sols)}
    if a.hjmao:
        slug2num = {p["slug"]: n for n, p in problems.items()}; nh = 0
        for n, slug, code in hjmao_java(a.hjmao, slug2num, excl):
            sols.append({"number": n, "title": problems[n]["title"], "slug": slug, "language": "java", "source": "huajianmao", "variant": "main", "approach": None, "explanation": None,
                         "thinking": None, "code": code, "time_complexity": None, "space_complexity": None, "complexity_evidence": None, "expected_to_pass_time_limit": True, "license": "unspecified"}); nh += 1
        rep["hjmao_java"] = nh
    jobs = []
    for i, s in enumerate(sols):
        s["id"] = i
        if s["language"] == "python3":
            m = re.search(r"^\s+def (\w+)\(self", s["code"], flags=re.M)
            if m and not re.search(r"ListNode|TreeNode|Node\b|-> None", s["code"].split("\n\n")[0] + "".join(l for l in s["code"].split("\n") if "def " in l)):
                s["method"] = m.group(1); s["code"] = B.typing_import(s["code"]) + s["code"]
                ex = B.parse_examples(problems[s["number"]]["statement"])
                if ex: jobs.append({"id": i, "code": s["code"], "method": s["method"], "examples": ex})
    got = {} if a.no_run else B.run_examples(jobs, a.workers)
    if not a.no_run and not a.no_java:
        import java_examples as JX
        jj = []
        for s in sols:
            if s["language"] == "java":
                ex = B.parse_examples(problems[s["number"]]["statement"])
                if ex: jj.append({"id": s["id"], "code": s["code"], "examples": ex, "hint": None})
        jr = JX.run(jj); rep["java_with_examples"] = len(jj); rep["java_skipped"] = sum(1 for v in jr.values() if "skip" in v)
        got.update({k: v for k, v in jr.items() if "skip" not in v})
    for s in sols:
        r = got.get(s["id"]); s["examples"] = ({k: r.get(k) for k in ("total", "passed", "unordered", "error", "firsterr")} if r else None)
        full = bool(r and r["total"] > 0 and r["passed"] + r["unordered"] == r["total"] and not r.get("error"))
        s["tier"] = ("A" if (s["complexity_evidence"] and s["explanation"] and full) else "B") if full else ("D" if r and r["total"] > 0 else "C")
        del s["id"]
        s.pop("method", None)
    bad = {}
    for s in sols:
        if s["language"] == "python3" and s["examples"]: bad.setdefault(s["number"], []).append(s["tier"] == "D")
    for s in sols:
        if s["tier"] == "D" and len(bad.get(s["number"], [])) >= 2 and all(bad[s["number"]]): s["tier"] = "C"; s["examples"]["unreliable"] = True
    with open(os.path.join(a.out, "problems.jsonl"), "w") as f:
        for p in problems.values(): f.write(json.dumps(p) + "\n")
    with open(os.path.join(a.out, "solutions.jsonl"), "w") as f:
        for s in sols: f.write(json.dumps(s) + "\n")
    n = 0; names = {"python3": "Python 3", "java": "Java", "cpp": "C++", "go": "Go", "typescript": "TypeScript", "javascript": "JavaScript", "rust": "Rust", "csharp": "C#", "php": "PHP", "c": "C", "kotlin": "Kotlin", "swift": "Swift", "ruby": "Ruby", "scala": "Scala"}
    with open(os.path.join(a.out, "sft.jsonl"), "w") as f:
        for s in sols:
            if s["tier"] == "D": continue
            p = problems[s["number"]]
            user = "Solve this problem in %s.\n\n%s (%s)\n\n%s" % (names[s["language"]], p["title"], p["difficulty"], p["statement"])
            asst = ("**Approach: %s**\n\n%s\n\n" % (s["approach"], s["explanation"]) if s["explanation"] else "") + "```%s\n%s\n```" % (s["language"].replace("python3", "python").replace("cpp", "cpp").replace("csharp", "csharp"), s["code"].rstrip())
            if not s["explanation"] and s["time_complexity"]: asst += "\n\nTime complexity: %s. Space complexity: %s." % (s["time_complexity"], s["space_complexity"])
            f.write(json.dumps({"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": asst}], "number": s["number"], "language": s["language"], "tier": s["tier"], "source": s["source"]}) + "\n"); n += 1
    from collections import Counter
    rep.update({"sft": n, "by_language": dict(Counter(s["language"] for s in sols)), "by_tier": dict(Counter(s["tier"] for s in sols)),
                "by_tier_python": dict(Counter(s["tier"] for s in sols if s["language"] == "python3")), "with_explanation": sum(1 for s in sols if s["explanation"]),
                "labelled": sum(1 for s in sols if s["complexity_evidence"]), "with_thinking": sum(1 for s in sols if s["thinking"]), "excluded_locked": len(excl)})
    json.dump(rep, open(os.path.join(a.out, "report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
if __name__ == "__main__": main()
