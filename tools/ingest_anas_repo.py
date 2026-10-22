#!/usr/bin/env python3
"""Turn a local clone of github.com/AnasImloul/Leetcode-Solutions (Unlicense / public domain) into
  <out>/problems.jsonl           one line per problem: number,title,slug,difficulty,statement(plain text),python_signature,java_signature,source_url
  <out>/reference_solutions.jsonl one line per (problem,language): the accepted-looking solution from the repo, header comment stripped, status "pending"
Locked evaluation problems (--exclude-numbers-file) and premium/non-algorithm problems are skipped.
  git clone --depth 1 https://github.com/AnasImloul/Leetcode-Solutions.git
  python3 tools/ingest_anas_repo.py --repo Leetcode-Solutions --exclude-numbers-file data/test/locked_leetcode_numbers.txt --out data/leetcode/anas"""
import argparse, html, json, os, re

def text_of(h):
    h = re.sub(r"<sup>(.*?)</sup>", r"^\1", h, flags=re.S); h = re.sub(r"<br\s*/?>|</p>|</li>|</pre>", "\n", h)
    h = re.sub(r"<li>", "- ", h); h = re.sub(r"<[^>]+>", "", h); h = html.unescape(h).replace("\xa0", " ")
    h = re.sub(r"\n\s*\n(\s*- )", r"\n\1", h)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", h)).strip()

def strip_header(code):
    lines = code.replace("\r\n", "\n").split("\n")
    while lines and (lines[0].startswith("// Runtime") or lines[0].startswith("# Runtime") or not lines[0].strip()): lines.pop(0)
    return "\n".join(lines).rstrip() + "\n"

def py_sig(code):
    m = re.search(r"^class Solution\b.*?\n\s+(def \w+\(.*?\).*?:)", code, flags=re.S | re.M)
    return ("class Solution:\n    " + m.group(1)) if m else None

def java_sig(code):
    m = re.search(r"class Solution\b[^{]*\{\s*\n?\s*((?:public|private|static|protected)[^\n;{]*\([^)]*\)[^\n{]*\{)", code)
    return ("class Solution {\n    " + m.group(1).strip()) if m else None

def with_imports_py(code):
    need = [n for n in ("List", "Optional", "Dict", "Set", "Tuple", "Deque") if re.search(r"\b%s\[" % n, code)]
    return (("from typing import %s\n\n" % ", ".join(need)) if need and "from typing" not in code else "") + code

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--exclude-numbers-file", default=None); a = ap.parse_args()
    excl = set()
    if a.exclude_numbers_file: excl = {int(x) for x in open(a.exclude_numbers_file).read().split() if x.strip().isdigit()}
    root = os.path.join(a.repo, "scripts", "algorithms"); os.makedirs(a.out, exist_ok=True)
    P = open(os.path.join(a.out, "problems.jsonl"), "w"); S = open(os.path.join(a.out, "reference_solutions.jsonl"), "w")
    n_p = n_s = n_x = n_skip = 0
    for dp, _, fs in sorted(os.walk(root)):
        if "info.json" not in fs: continue
        info = json.load(open(os.path.join(dp, "info.json"))); num = int(info["id"])
        if num in excl: n_x += 1; continue
        if info.get("premium") or "README.md" not in fs: n_skip += 1; continue
        name = info["name"]; stem = os.path.join(dp, name)
        code = {}
        for lang, ext in (("python3", ".py"), ("java", ".java")):
            if os.path.exists(stem + ext): code[lang] = strip_header(open(stem + ext, encoding="utf-8", errors="replace").read())
        if not code: n_skip += 1; continue
        stm = text_of(open(os.path.join(dp, "README.md"), encoding="utf-8", errors="replace").read())
        stm = re.sub(r"^\s*\d+\.\s*" + re.escape(name) + r"\s*\n", "", stm).strip()
        P.write(json.dumps({"number": num, "title": name, "slug": info["url"].rstrip("/").split("/")[-1], "difficulty": info["difficulty"].capitalize(),
            "statement": stm, "python_signature": py_sig(code.get("python3", "")), "java_signature": java_sig(code.get("java", "")),
            "source_url": info["url"]}) + "\n"); n_p += 1
        for lang, c in code.items():
            S.write(json.dumps({"number": num, "title": name, "language": lang, "origin": "anas_repo_reference",
                "code": with_imports_py(c) if lang == "python3" else c, "status": "pending"}) + "\n"); n_s += 1
    print("problems", n_p, "reference solutions", n_s, "excluded(locked)", n_x, "skipped", n_skip)
if __name__ == "__main__": main()
