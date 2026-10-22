#!/usr/bin/env python3
"""Print a random, reproducible sample of harvested LeetCode rows for a human check, plus automatic sanity checks over ALL rows.

  python tools/audit_lc_sample.py --data ~/sft_lc2/lc_repos.jsonl --n 200 --out ~/sft_lc2/audit_200.md

Automatic checks (all rows): fence language matches meta.language, Java has `class`, Python parses, answer not empty, question names the same language.
The sample file is for you to read: is it the right problem, a complete solution, in the right language? Aim for >=95% fine before training on it.
"""
import argparse, ast, json, os, random, re, warnings
warnings.filterwarnings("ignore")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(os.path.expanduser(a.data), encoding="utf-8")]
    bad = {}
    def flag(k): bad[k] = bad.get(k, 0) + 1
    for r in rows:
        q, _, ans = r["text"].partition("\n\nAnswer:\n"); m = r["meta"]; lang = m["language"]
        if not ans.strip(): flag("empty_answer"); continue
        if m["kind"] != "solution": continue
        blocks = re.findall(r"```(\w+)\n(.*?)```", ans, re.S)
        if not blocks: flag("no_code_block"); continue
        if blocks[-1][0] != lang: flag("fence_language_mismatch")
        if ("in Python" in q.splitlines()[-1]) != (lang == "python") and "Solve this problem in" in q: flag("question_language_mismatch")
        if lang == "java" and "class" not in blocks[-1][1]: flag("java_without_class")
        if lang == "python":
            try: ast.parse(blocks[-1][1])
            except Exception: flag("python_does_not_parse")
    random.Random(a.seed).shuffle(rows)
    with open(os.path.expanduser(a.out), "w", encoding="utf-8") as f:
        f.write(f"# Audit sample: {min(a.n, len(rows))} of {len(rows)} rows (seed {a.seed})\n\nAutomatic checks over all rows: {json.dumps(bad) if bad else 'all passed'}\n\n")
        for i, r in enumerate(rows[:a.n], 1):
            m = r["meta"]
            f.write(f"\n---\n## {i}. problem {m['problem_number']} | {m['source_dataset']} | {m['language']} | {m['kind']}\n\n```text\n{r['text'][:6000]}\n```\n\n- [ ] right problem   - [ ] complete solution   - [ ] right language\n")
    print("rows", len(rows), "| automatic checks:", bad or "all passed", "| sample ->", a.out)


if __name__ == "__main__":
    main()
