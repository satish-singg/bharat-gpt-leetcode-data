#!/usr/bin/env python3
"""How many locked LeetCode tasks already have a solution file in the training corpus? CPU only, read-only, nothing is executed.

  python3 tools/leetcode_leak_check.py --locked ~/locked_eval_1365.jsonl --train ~/cs-data/cs-v5/clean/train.jsonl --out ~/leetcode_leak.json

A corpus file counts as a "probable solution" of locked task T when it (1) is a Python code document, (2) contains `class Solution`, and
(3) defines a method with the same name as T's entry point (`Solution().methodName` -> `def methodName(`). This is the LeetCode convention, so a match
is strong evidence of a solution to the same problem OR to another problem that happens to reuse the method name (generic names such as `search`
can collide), so counts are an UPPER-ish bound per task. Files that solve the task under another method name, or in Java, are not seen.
It complements the 13-gram seen/unseen split of the execution track, which looks at the task text, not at solution files.
Output: tasks_total, tasks_with_probable_solution, tasks_with_5_plus, files_matched, and per-task counts (generic names flagged).
"""
import argparse, collections, json, os, re

DEF = re.compile(r"def\s+([A-Za-z_]\w*)\s*\(")
GENERIC = {"search", "solve", "solution", "find", "get", "run", "main", "helper", "dfs", "bfs", "insert", "delete", "add", "remove", "update", "merge"}


def method_of(entry_point):
    """'Solution().twoSum' -> 'twoSum'; None when the entry point has no method part."""
    ep = (entry_point or "").strip()
    return ep.rsplit(".", 1)[1] if "." in ep else None


def locked_leetcode(path):
    out = {}
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            t = json.loads(line)
            if t.get("track") != "leetcode": continue
            m = method_of(t.get("entry_point"))
            if m: out[t["id"]] = m
    return out


def scan(train_path, methods, progress=True):
    """methods: {task id -> method name}. Returns {task id -> files with class Solution + def method}."""
    by_method = collections.defaultdict(list)
    for tid, m in methods.items(): by_method[m].append(tid)
    counts, files = collections.Counter(), 0
    with open(os.path.expanduser(train_path), encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if progress and i % 200000 == 0: print(f"  {i:,} lines, {files:,} Solution files so far", flush=True)
            if "class Solution" not in line or '"code_python"' not in line: continue
            try: d = json.loads(line)
            except ValueError: continue
            if d.get("source") != "code_python": continue
            text = d.get("text") or ""
            if "class Solution" not in text: continue
            files += 1
            for name in set(DEF.findall(text)) & by_method.keys():
                for tid in by_method[name]: counts[tid] += 1
    return counts, files


def summarize(methods, counts, files):
    per = {tid: {"method": m, "files": counts.get(tid, 0), "generic_name": m in GENERIC} for tid, m in sorted(methods.items())}
    hit = [t for t, v in per.items() if v["files"]]
    return {"tasks_total": len(methods), "tasks_with_probable_solution": len(hit),
            "tasks_with_probable_solution_non_generic": sum(1 for t in hit if not per[t]["generic_name"]),
            "tasks_with_5_plus": sum(1 for t in hit if per[t]["files"] >= 5),
            "class_solution_files_in_corpus": files, "per_task": per}


def merge_into_overlap_report(rep, overlap_report):
    """Add every task with a probable solution file to an exec-track overlap report (the file `cli.py overlap --out` writes), so that
    `cli.py split --report <merged>` puts those tasks in the SEEN half. Returns a new dict; the input is not modified."""
    merged = json.loads(json.dumps(overlap_report))
    hits = merged.setdefault("hits", {})
    for tid, v in rep["per_task"].items():
        if v["files"]:
            hits.setdefault(tid, []).append({"part": "solution_file_name_match", "files": v["files"], "method": v["method"]})
    merged["flagged"] = len(hits)
    merged["note"] = (merged.get("note", "") + " | merged with leetcode_leak_check (class Solution + same method name)").strip(" |")
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locked", required=True); ap.add_argument("--train", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--merge-overlap", help="exec-track overlap report (cli.py overlap --out) to merge the leak hits into")
    ap.add_argument("--merged-out", help="where to write the merged report (use it as `cli.py split --report`)")
    a = ap.parse_args()
    methods = locked_leetcode(a.locked)
    print("locked LeetCode tasks with a method name:", len(methods), flush=True)
    counts, files = scan(a.train, methods)
    rep = summarize(methods, counts, files)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_task"}, indent=1))
    json.dump(rep, open(os.path.expanduser(a.out), "w"), indent=1)
    print("saved", a.out)
    if a.merge_overlap and a.merged_out:
        merged = merge_into_overlap_report(rep, json.load(open(os.path.expanduser(a.merge_overlap))))
        json.dump(merged, open(os.path.expanduser(a.merged_out), "w"), indent=1)
        print("merged report ->", a.merged_out, "| flagged tasks now:", merged["flagged"])


if __name__ == "__main__":
    main()
