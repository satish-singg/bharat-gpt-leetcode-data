#!/usr/bin/env python3
"""Put ChatGPT's hand-written data (data/) and the mined corpora (corpus/anas_kamyu, corpus/doocs_huajianmao) into ONE schema = ChatGPT's solution schema,
and render training chats in two variants:  sft_plain  (answer only)  and  sft_think  (the reasoning note inside <think> ... </think> before the answer).
  python3 tools/unify_corpus.py --repo /path/to/bharat-gpt-leetcode-data --locked locked/locked_leetcode_numbers.txt
Writes <repo>/corpus/unified/: problems.jsonl.gz, solutions.jsonl.gz, sft_plain.jsonl.gz, sft_think.jsonl.gz, qa_sft.jsonl.gz, report.json
Where the think text comes from: ChatGPT records -> its six-line `notes`; doocs records -> the 'Thinking' block (idea / bottleneck / pitfall, ~55 words). kamyu/Anas records have no note -> only in sft_plain.
approach_id for mined records is a keyword heuristic (field approach_id_source="heuristic")."""
import argparse, glob, gzip, json, os, re

KW = [("memoiz|top-down|top down|记忆", "dp_top_down"), ("space optim|rolling", "dp_space_optimized"), ("dynamic programming|\\bdp\\b|knapsack", "dp_bottom_up"),
      ("monotonic stack", "monotonic_stack"), ("union.?find|disjoint", "union_find"), ("topological", "topological_sort"), ("dijkstra|bellman|floyd|shortest path|spfa", "shortest_path"),
      ("segment tree", "segment_tree"), ("binary indexed|fenwick|tree array", "binary_indexed_tree"), ("trie|prefix tree", "trie"), ("heap|priority queue", "heap"),
      ("sliding window", "sliding_window"), ("two.?pointer|double.?pointer", "two_pointers"), ("binary search", "binary_search"), ("difference array", "difference_array"),
      ("prefix sum", "prefix_sum"), ("hash", "hash_map"), ("sort", "sorting"), ("greedy", "greedy"), ("backtrack", "backtracking"), ("bit ", "bit_manipulation"), ("bitwise|bit manip", "bit_manipulation"),
      ("bfs|breadth", "graph_bfs"), ("dfs|depth|recurs", "graph_dfs"), ("stack", "stack"), ("queue", "queue"), ("math|formula|number theory|gcd|prime", "math_formula"),
      ("simulat", "simulation"), ("divide and conquer|merge sort", "divide_and_conquer"), ("enumerat|brute|violence", "brute_force"), ("linked list", "linked_list_pointers")]
TOPIC = {"array": "array", "hash table": "hash_table", "two pointers": "two_pointers", "sliding window": "sliding_window", "binary search": "binary_search", "sorting": "sorting", "sort": "sorting",
         "greedy": "greedy", "stack": "stack", "monotonic stack": "monotonic_stack", "queue": "queue", "monotonic queue": "queue", "heap (priority queue)": "heap", "binary heap": "heap",
         "linked list": "linked_list", "binary search tree": "bst", "breadth-first search": "graph_bfs", "depth-first search": "graph_dfs", "union find": "union_find", "topological sort": "topological_sort",
         "shortest path": "shortest_path", "backtracking": "backtracking", "bit manipulation": "bit_manipulation", "math": "math", "number theory": "number_theory", "combinatorics": "combinatorics",
         "prefix sum": "prefix_sum", "trie": "trie", "segment tree": "segment_tree", "binary indexed tree": "binary_indexed_tree", "string matching": "string_matching", "simulation": "simulation",
         "divide and conquer": "divide_and_conquer", "geometry": "geometry", "dynamic programming": "dp_1d"}
LANGN = {"python3": "Python 3", "java": "Java", "cpp": "C++", "go": "Go", "typescript": "TypeScript", "javascript": "JavaScript", "rust": "Rust", "csharp": "C#", "php": "PHP", "c": "C", "kotlin": "Kotlin", "swift": "Swift", "ruby": "Ruby", "scala": "Scala"}
FENCE = {"python3": "python", "csharp": "csharp"}

def approach_id(text, code, tle):
    t = (text or "").lower()
    for pat, aid in KW:
        if re.search(pat, t): return aid
    if tle: return "brute_force"
    c = code or ""
    for pat, aid in (("heapq|PriorityQueue|priority_queue", "heap"), ("bisect|binarySearch|lower_bound|upper_bound", "binary_search"), ("lru_cache|@cache|memo", "dp_top_down"), ("deque|ArrayDeque|queue<", "queue"), ("UnionFind|union_find|find\\(", "union_find")):
        if re.search(pat, c): return aid
    return "other_unclassified"

def tags_from(topics):
    out = []
    for t in topics or []:
        k = TOPIC.get(t.strip().lower())
        if k and k not in out: out.append(k)
    return out

def readj(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for l in f:
            if l.strip(): yield json.loads(l)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--locked", required=True); a = ap.parse_args()
    locked = {int(x) for x in open(a.locked).read().split() if x.strip().isdigit()}; R = a.repo; out = os.path.join(R, "corpus", "unified"); os.makedirs(out, exist_ok=True)
    probs, sols = {}, []   # probs[(number, origin)]
    # ChatGPT data
    for f in sorted(glob.glob(os.path.join(R, "data", "problems", "batch_*.jsonl"))):
        for p in readj(f):
            if p["number"] in locked: continue
            probs[(p["number"], "chatgpt")] = dict(p, origin="chatgpt")
    for f in sorted(glob.glob(os.path.join(R, "data", "solutions", "batch_*.jsonl"))):
        for s in readj(f):
            if "omitted" in s or s["number"] in locked: continue
            sc = s.get("self_check") or {}
            s = dict(s, source="chatgpt", license="own", approach_id_source="chatgpt", think=s.get("notes"), explanation=None, tier="T" if sc.get("ran") else "U", examples=None)
            sols.append(s)
    ann = {}
    ap_ = os.path.join(R, "corpus", "annotations.jsonl.gz")
    if os.path.exists(ap_): ann = {r["id"]: r["notes"] for r in readj(ap_)}
    # mined
    for folder in ("anas_kamyu", "doocs_huajianmao"):
        d = os.path.join(R, "corpus", folder)
        if not os.path.exists(os.path.join(d, "problems.jsonl")): continue
        for p in readj(os.path.join(d, "problems.jsonl")):
            if p["number"] in locked: continue
            p = dict(p); p["tags"] = tags_from(p.pop("topics", [])); p["origin"] = folder; probs[(p["number"], folder)] = p
        for s in readj(os.path.join(d, "solutions.jsonl.gz")):
            if s["number"] in locked: continue
            ex = s.get("examples") or {}
            title = s.get("approach") or ""
            aid = approach_id(title, s["code"], not s.get("expected_to_pass_time_limit", True))
            pr = probs.get((s["number"], folder)) or {}
            note = ann.get("%d:%s:%s" % (s["number"], s["source"], title or s.get("variant")))
            sols.append({"number": s["number"], "title": s["title"], "language": s["language"], "approach_id": aid, "approach_name": title or s.get("variant"), "pattern_tags": pr.get("tags", []),
                         "notes": note, "think": s.get("thinking") or note, "explanation": s.get("explanation"), "code": s["code"], "time_complexity": s.get("time_complexity"), "space_complexity": s.get("space_complexity"),
                         "complexity_reason": None, "complexity_evidence": s.get("complexity_evidence"), "expected_to_pass_time_limit": s.get("expected_to_pass_time_limit", True),
                         "self_check": {"ran": bool(ex and ex.get("total")), "examples_passed": (ex.get("passed", 0) + ex.get("unordered", 0)) if ex else 0, "examples_total": ex.get("total", 0) if ex else 0},
                         "examples": ex or None, "tier": s["tier"], "source": s["source"], "license": s.get("license", "see source repo"), "approach_id_source": "heuristic", "status": "pending", "_origin": folder})
    def prob_for(s):
        for o in ((s["_origin"],) if "_origin" in s else ()) + ("doocs_huajianmao", "anas_kamyu", "chatgpt"):
            if (s["number"], o) in probs: return probs[(s["number"], o)]
        return None
    def sig(s, p):
        return p.get("python_signature") if s["language"] == "python3" else p.get("java_signature") if s["language"] == "java" else None
    def render(s, p, think):
        lang = s["language"]; code = s["code"].rstrip()
        user = "Solve this problem in %s.\n\n%s (%s)\n\n%s" % (LANGN.get(lang, lang), s["title"], p.get("difficulty", ""), p["statement"])
        sg = sig(s, p)
        if sg and lang in ("python3", "java"): user += "\n\nUse this signature:\n" + sg
        parts = []
        if think: parts.append("<think>\n%s\n</think>" % think.strip())
        if s.get("approach_name") and s["source"] != "kamyu104": parts.append("**Approach: %s**" % s["approach_name"])
        if s.get("explanation"): parts.append(s["explanation"].strip())
        parts.append("```%s\n%s\n```" % (FENCE.get(lang, lang), code))
        tail = ""
        if s.get("time_complexity") and s.get("space_complexity") and not (s.get("explanation") and "omplexity" in s["explanation"]):
            tail = "Time complexity: %s. Space complexity: %s." % (s["time_complexity"], s["space_complexity"])
            if s.get("complexity_reason"): tail += " " + s["complexity_reason"]
        if tail: parts.append(tail)
        return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": "\n\n".join(parts)}], "number": s["number"], "language": lang, "tier": s["tier"], "source": s["source"]}
    n = {"plain": 0, "think": 0, "qa": 0}
    with gzip.open(os.path.join(out, "sft_plain.jsonl.gz"), "wt") as fp, gzip.open(os.path.join(out, "sft_think.jsonl.gz"), "wt") as ft:
        for s in sols:
            if s["tier"] == "D": continue
            p = prob_for(s)
            if not p or not p.get("statement"): continue
            fp.write(json.dumps(render(s, p, None)) + "\n"); n["plain"] += 1
            if s.get("think"): ft.write(json.dumps(render(s, p, s["think"])) + "\n"); n["think"] += 1
    with gzip.open(os.path.join(out, "qa_sft.jsonl.gz"), "wt") as fq:
        for f in sorted(glob.glob(os.path.join(R, "data", "qa", "batch_*.jsonl"))):
            for q in readj(f):
                if q["number"] in locked: continue
                fq.write(json.dumps({"messages": [{"role": "user", "content": q["question"]}, {"role": "assistant", "content": q["answer"]}], "number": q["number"], "kind": q.get("kind"), "source": "chatgpt"}) + "\n"); n["qa"] += 1
    for name, rows in (("problems", [dict(v) for v in probs.values()]), ("solutions", [{k: v for k, v in s.items() if k != "_origin"} for s in sols])):
        with gzip.open(os.path.join(out, name + ".jsonl.gz"), "wt") as f:
            for r in rows: f.write(json.dumps(r) + "\n")
    from collections import Counter
    rep = {"problems": len(probs), "solutions": len(sols), "sft_plain": n["plain"], "sft_think": n["think"], "qa": n["qa"], "by_source": dict(Counter(s["source"] for s in sols)),
           "by_language": dict(Counter(s["language"] for s in sols)), "by_tier": dict(Counter(s["tier"] for s in sols)), "approach_id": dict(Counter(s["approach_id"] for s in sols).most_common(12)), "locked_removed_from_input": len(locked)}
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1); print(json.dumps(rep, indent=1))
if __name__ == "__main__": main()
