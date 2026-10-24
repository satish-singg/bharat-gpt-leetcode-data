#!/usr/bin/env python3
"""Builds annotate2/batch_NNNN.jsonl: the solutions that still have no note (annotate/ minus annotated/), re-ordered so the most useful come first:
Medium/Hard problems in the techniques the corpus covers least (graphs, union-find, heap, DP, trie, ...), one solution per problem before any second solution, Easy last.
Each line = the annotate/ record + difficulty + tags. 20 per batch. Never includes a locked problem number.
  python3 tools/make_annotate2.py"""
import ast, collections, glob, gzip, json, os

HARD_TAGS = {"graph_bfs", "graph_dfs", "union_find", "heap", "topological_sort", "trie", "monotonic_stack", "number_theory", "combinatorics", "geometry", "string_matching",
             "dp_2d", "dp_tree", "dp_bitmask", "dp_interval", "segment_tree", "binary_indexed_tree", "dijkstra", "backtracking", "binary_search", "sliding_window", "dp_1d", "tree_dfs", "tree_bfs"}
W = {"Hard": 3.0, "Medium": 2.0, "Easy": 0.5}
locked = {int(x) for x in open("locked/locked_leetcode_numbers.txt").read().split() if x.strip().isdigit()}
P = {}
for l in gzip.open("corpus/unified/problems.jsonl.gz", "rt"):
    if l.strip():
        r = json.loads(l); P[int(r["number"])] = r
def tags_of(n):
    t = P.get(n, {}).get("tags", []); 
    try: return ast.literal_eval(t) if isinstance(t, str) else list(t or [])
    except Exception: return []
done = {json.loads(l)["id"] for f in glob.glob("annotated/*.jsonl") for l in open(f, encoding="utf-8") if l.strip()}
cover = collections.Counter()                                   # how many problems with each tag are already annotated (ChatGPT data + annotated/)
for f in glob.glob("annotated/*.jsonl"):
    for l in open(f, encoding="utf-8"):
        if l.strip():
            i = json.loads(l)["id"]
            for t in tags_of(int(i.split(":")[0])): cover[t] += 1
items = []
for f in sorted(glob.glob("annotate/*.jsonl")):
    for l in open(f, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            if r["id"] in done or int(r["number"]) in locked: continue
            items.append(r)
def score(r):
    n = int(r["number"]); d = P.get(n, {}).get("difficulty", "Medium"); tg = tags_of(n)
    rare = sum(1.0 / (1 + cover[t]) * 50 for t in tg if t in HARD_TAGS)
    return -(W.get(d, 1.0) * (1 + rare) + (1.0 if any(t in HARD_TAGS for t in tg) else 0))
items.sort(key=score)
first, second, seen = [], [], set()
for r in items:
    (second if int(r["number"]) in seen else first).append(r); seen.add(int(r["number"]))
ordered = first + second
os.makedirs("annotate2", exist_ok=True)
for f in glob.glob("annotate2/*.jsonl"): os.remove(f)
for b in range(0, len(ordered), 20):
    with open(f"annotate2/batch_{b // 20 + 1:04d}.jsonl", "w", encoding="utf-8") as g:
        for r in ordered[b:b + 20]:
            n = int(r["number"]); g.write(json.dumps(dict(r, difficulty=P.get(n, {}).get("difficulty"), tags=tags_of(n)), ensure_ascii=False) + "\n")
dc = collections.Counter(P.get(int(r["number"]), {}).get("difficulty") for r in ordered); print("total", len(ordered), "difficulty", dict(dc), "batches", (len(ordered) + 19) // 20)
first100 = ordered[:400]; print("first 20 batches: difficulty", dict(collections.Counter(P.get(int(r["number"]), {}).get("difficulty") for r in first100)),
      "top tags", collections.Counter(t for r in first100 for t in tags_of(int(r["number"]))).most_common(12))
