#!/usr/bin/env python3
"""Cut the LeetCode problem statements (doocs/leetcode, fetched by harvest_leetcode_repos.py) into batch files for an AI AGENT that writes solutions (docs/AGENT_PROMPT_LEETCODE.md).
CPU only.  Reference solutions are NOT included (the agent solves independently); problems of the locked LeetCode test split are removed by number.

  python3 tools/make_agent_batches.py --src ~/ProjectAI/data/leetcode/repos --out-dir ~/ProjectAI/data/leetcode/agent_batches --size 20 [--exclude-numbers-file FILE] [--only-without-multi 1]
Each line of batch_NNNN.jsonl: {number, title, slug, difficulty, tags, statement, python_signature, java_signature}.   Signatures are taken from the first doocs solution in each language
(class line + the method line), so the agent keeps the exact LeetCode interface; an empty signature means the problem has no standard method signature (design / interactive)."""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harvest_leetcode_repos as H


def python_signature(code):
    lines = code.splitlines(); out = []
    for i, l in enumerate(lines):
        if l.startswith("class Solution"):
            out.append(l)
            for m in lines[i + 1:]:
                if m.strip().startswith("def "):
                    out.append(m.rstrip().rstrip(":") + ":")  # one line is enough; long signatures are kept whole
                    return "\n".join(out)
    return ""


def java_signature(code):
    lines = code.splitlines(); out = []
    for i, l in enumerate(lines):
        if re.match(r"\s*class Solution", l):
            out.append("class Solution {")
            for m in lines[i + 1:]:
                if re.match(r"\s*(public|private|static|protected)?\s*[\w<>\[\], ?]+\s+\w+\s*\(.*\)\s*(throws [\w, ]+)?\s*\{?\s*$", m) and "class" not in m:
                    out.append("    " + m.strip().rstrip("{").rstrip() + " {...}")
                    return "\n".join(out) + "\n}"
    return ""


def make_batches(problems, excluded, size, only=None):
    items = []
    for p in sorted(problems, key=lambda q: q["number"]):
        if p["number"] in excluded: continue
        sol = p.get("solutions") or []
        py = next((s["code"]["python"] for s in sol if "python" in s["code"]), ""); jv = next((s["code"]["java"] for s in sol if "java" in s["code"]), "")
        items.append({"number": p["number"], "title": p["title"], "slug": p["slug"], "difficulty": p["difficulty"], "tags": p.get("tags", []),
                      "statement": p["description"], "python_signature": python_signature(py), "java_signature": java_signature(jv)})
    return [items[i:i + size] for i in range(0, len(items), size)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True); ap.add_argument("--out-dir", required=True); ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--exclude-numbers-file", default=None)
    a = ap.parse_args()
    src = os.path.expanduser(a.src); droot = os.path.join(src, "doocs"); probs = []
    for root, _, files in os.walk(droot):
        if "README_EN.md" in files:
            p = H.parse_doocs(open(os.path.join(root, "README_EN.md"), encoding="utf-8", errors="ignore").read())
            if p: probs.append(p)
    excluded = {int(l) for l in open(os.path.expanduser(a.exclude_numbers_file)) if l.strip()} if a.exclude_numbers_file else H.test_split_numbers()
    batches = make_batches(probs, excluded, a.size)
    out = os.path.expanduser(a.out_dir); os.makedirs(out, exist_ok=True)
    for i, b in enumerate(batches, 1):
        with open(os.path.join(out, f"batch_{i:04d}.jsonl"), "w", encoding="utf-8") as f:
            for it in b: f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"{len(probs)} problems parsed, {len(excluded)} excluded (locked test split), {sum(len(b) for b in batches)} in {len(batches)} batches of <= {a.size} -> {out}")


if __name__ == "__main__":
    main()
