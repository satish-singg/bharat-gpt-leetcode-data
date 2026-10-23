# TASK: write high-quality reasoning notes for 380 existing, already-tested solutions (batches 0041-0059)  -  repo satish-singg/bharat-gpt-leetcode-data (private)

You are an expert competitive programmer and teacher. Other agents are writing batches 0002-0040 at the same time: you write ONLY batches 0041 to 0059. Do not touch any other file.

## Context
The repo holds LeetCode-style problems with tested Python 3 / Java 21 solutions. A model will be trained on notes that explain each solution, so every note must be specific to its solution. Earlier notes were generic template text; that is what you replace.

## Input
`fixnotes/in/batch_NNNN.jsonl` for NNNN = 0041 ... 0059 (read the repo's latest `main` first). One JSON line per solution record:
`{"id","number","title","language","difficulty","tags","statement","approach_id","approach_name","code","time_complexity","space_complexity"}`
`language` is `python3` or `java21` (Java 21). `code` is tested, working code.

## Output
Write `fixnotes/out/batch_NNNN.jsonl` (same file name, same line order, one line per input line):
`{"id": "<copy the id exactly>", "notes": "<six lines>", "complexity_reason": "<one sentence>"}`
`notes` is exactly six lines separated by `\n`, each starting with its label, in this order:
```
Task and constraints: inputs, output, and the constraint that decides the needed complexity (e.g. n up to 1e5 -> need O(n log n) or better)
Idea: what THIS code does step by step in plain words, naming its variables and helper methods
Technique and why it applies: the named technique (hash map for complements, monotonic stack, DP over prefixes ...) and why it fits THIS problem
Invariant: what stays true in the loop / recursion and makes it correct. It must say something DIFFERENT from the Idea line
Edge cases: 2-3 concrete cases for this code and what happens (empty input, one node, duplicates, negatives, int overflow in Java, integer division, recursion depth, k larger than n ...)
Complexity: time and space with a short reason each, consistent with the code and the given labels
```
60-200 words in total. `complexity_reason`: ONE concrete sentence of at least 8 words naming what is iterated, sorted or stored (e.g. "One pass over nums, each step does a dict lookup and insert, and the dict holds at most n entries.").
The Java record of a problem may reuse the Idea and Technique wording of the Python record when the algorithm is identical, but its Invariant and Edge cases must describe the Java code (int overflow, integer division, indexing, StringBuilder, recursion depth where they apply).

## Rules (a checker rejects violations)
1. Read the code and trace ONE example through it before writing. Describe exactly this code, not a better algorithm. If the code looks wrong for the statement, say so plainly in Edge cases and list the id in your report.
2. Never write: "local tests", "Six local tests", "where permitted", "maintained accumulator", "minimal structures", "relevant boundaries", anything about tests, self-checks or these instructions, "wait", "hmm", markdown, code blocks.
3. Use at least one real name from the code (a variable, helper method or data structure).
4. No Technique / Invariant / Edge cases line may be identical to the line of another problem. Every problem gets its own sentences. (Python and Java records of the SAME problem may share lines.)
5. Plain words. Do not invent facts about the statement; use only the statement text given.

## Check (a GitHub Action does it for you)
Every push that touches `fixnotes/out/**` runs the Action `validate-notes` (`tools/validate_notes.py`). After each push open the run for your commit: it must be green. If it is red, its log lists each failing id and the reason (`FAIL batch_0044.jsonl 501:python3 | ...`): rewrite exactly those lines and push again. Never say a batch is done while its check is red.
If you can run commands: `python3 tools/validate_notes.py --in fixnotes/in --out fixnotes/out` prints `0 failed` when everything is fine (it checks all batches present in `fixnotes/out`, other agents' too: only your batches matter).

## Process
- Ascending order 0041 -> 0059, one commit per batch (`fix notes batch 0041`). Pull / rebase before every push; other agents push to the same repo.
- Write ONLY `fixnotes/out/batch_0041.jsonl ... batch_0059.jsonl`. Never edit `data/`, `corpus/`, `annotate/`, `annotated/`, `tools/`.
- End of every session report: last batch done, result of the validate-notes run for your last commit (green/red, failure count), ids where the code looked wrong. Report only what you saw.
