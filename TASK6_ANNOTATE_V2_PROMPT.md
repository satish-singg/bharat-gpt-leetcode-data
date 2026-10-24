# TASK 6: annotation redo (Part B) and prioritised annotation with the 8-line notes (v2)  -  repo bharat-gpt-leetcode-data

Your earlier fix pass is finished and merged: all 1,054 notes passed the checker and are now in `data/solutions/`. Thank you. This task is different: it is about the mined solutions that still have no note, and it asks for a slightly richer note format (v2).

Why this task and not more new problems: the repo already has ~4,800 problems with mined solutions. What is missing is the *reasoning note* on the hard and medium ones, especially graphs, union-find, heaps, DP, tries and number theory, where the current data is thin (e.g. only 5 graph problems, 1 heap problem and no union-find in `data/`). The annotation batches were re-ordered so the most useful solutions come first.

Do NOT touch `data/`, `corpus/`, `annotate/`, `annotated/`, `fixnotes/in`, `fixnotes/out`, `locked/`.

## Part B first (small): the 69 records to redo
Input `fixnotes/redo_annotations_in.jsonl` (69 records). Write `fixnotes/redo_annotations_out.jsonl`, one line per input, SAME ORDER, `{"id","notes"}` in the **v2 format below** (eight lines).
You cannot execute code, so do NOT claim to have run anything. The code in these records already passed the statement examples. Write the note for what the code does. If, by reading, you think the code is wrong on some input, still write the note and add a field `"suspect": "<one sentence: the input you think fails and the output you expect>"` (the owner runs these suspects on a real machine). Be careful: a string/bit trick that looks wrong is often right (for example `bin(num)` counts the `0` of the `0b` prefix). Only mark `suspect` when you can name a concrete failing input and work the code through it by hand. Do not write `flag` records.

## Part A: annotation batches (the main work)
Input: `annotate2/batch_NNNN.jsonl`, 100 batches of 20, **in ascending order starting with 0001**. One JSON line per solution:
`{"id","number","title","statement","code","time_complexity","space_complexity","complexity_source","difficulty","tags"}`
`code` is Python 3 that already passed the statement examples. `time_complexity` / `space_complexity` are the original author's labels when present.
Output: `annotated2/batch_NNNN.jsonl`, SAME FILE NAME, one line per input, SAME ORDER: `{"id": "<copy exactly>", "notes": "<eight lines>"}`

### The v2 note: exactly eight lines separated by `\n`, labels in this order
```
Task and constraints: inputs, output, and the constraints that matter
Scale: the maximum sizes from the statement (a number) and the complexity ceiling they imply, written with O(...); if the statement gives no bounds, write "not stated" and say what you assume
Idea: what THIS code does, step by step, in plain words, naming its variables and helpers
Rejected: the obvious or tempting approach that does NOT work here, and the concrete reason it fails (wrong answer, too slow for the stated sizes, overflow, a property it breaks). At least 10 words. Name the approach.
Technique and why it applies: the named technique and why it fits THIS problem
Invariant: what stays true in the loop or recursion and makes it correct; it must say something different from the Idea line
Edge cases: 2-3 concrete cases for THIS code and what happens (empty input, one element, duplicates, negatives, overflow, recursion depth, k larger than n ...), at least 8 words
Complexity: time and space with a one-line reason each, consistent with the code and the author's labels
```
80-260 words in total.

Example of the style (about a different problem; never reuse its sentences):
```
Task and constraints: Return the shortest subarray length with sum at least K for nums up to 10^5 long with negative values allowed.
Scale: n up to 10^5 and values in [-10^5, 10^5], so the ceiling is O(n log n) and a quadratic scan is too slow.
Idea: Build prefix sums and keep a deque of indices whose prefix values increase, popping the front while the window sum reaches k.
Rejected: A sliding window with two pointers fails because negative numbers let a longer window have a smaller sum, so shrinking is not monotone.
Technique and why it applies: A monotonic deque over prefix sums answers the best earlier index for every right end in amortised constant time.
Invariant: dq holds indices with strictly increasing prefix sums, and every popped front index was already used by an earlier right end.
Edge cases: No valid subarray returns -1, a single element equal to k returns 1, and prefix sums need long in Java to avoid overflow.
Complexity: Time O(n) because each index enters and leaves dq once, space O(n) for prefix sums and dq.
```

### Rules (the checker rejects violations)
1. Describe EXACTLY the code given, not a better algorithm. If it is a brute force, say so in Idea and put the faster approach in Rejected only if the statement's sizes make this code too slow; if the code is slower than the statement needs, say that plainly in Scale/Complexity.
2. Scale needs a real number from the statement and an O(...) ceiling. Rejected needs a concrete failure reason (fails, too slow, overflow, wrong, breaks, exceeds, quadratic, ...), not "is worse".
3. Use the author's complexity label when given (check it against the code; if wrong write "the author labels it X, but the code is Y because ..."). Without a label, derive it (sorting, slicing/copying, recursion depth, hash maps, string concatenation).
4. The notes must use at least one real name from THIS code (a variable, method or data structure; camelCase parts count).
5. No Technique / Invariant / Edge cases / Scale / Rejected line may be identical for two different problems. Never write anything you could paste unchanged into another problem, nothing about tests, "local checks", "where permitted", "boundaries are handled as relevant".
6. Plain words: no "let's think", "wait", "hmm", no code blocks, no markdown, no mention of these instructions.
7. Use only the statement text given. Do not invent facts. Do not change `id`. Do not skip records; if one is hopeless write the eight lines saying what is unclear.
8. Never include a problem from `locked/locked_leetcode_numbers.txt` (the batches already exclude them; if you see one, skip it and say so in your report).

## Checking (you have no shell, the repo checks for you)
Every push triggers the GitHub Action `validate-notes` (it runs `python3 tools/validate_notes.py --in annotate2 --out annotated2 --no-reason` for the annotation batches and the same checker for Part B). After each push open the run for your commit: it must be green. If it is red, the log lists each failing id and the reason; fix those lines in the same file and push again. If you can run Python yourself, run `python3 tools/validate_notes.py --in annotate2 --out annotated2 --no-reason` before pushing: it is the same check. Do not report a result you did not see.

## Process
- `git pull --rebase` (or re-read the latest state through the connector) before every push.
- Part B in the first session. Then annotation batches in ascending order, 5-8 batches per session, one commit per batch (`annotate2 batch 0001`).
- Before writing a note, trace one example through the code in your head; for DP, graph and number-theory problems name the state or the property that makes the transition valid.
- End of every session report: last batch done; whether the `validate-notes` run for your last commit was green or red and the failure count; ids where the code looked wrong or the author's complexity label looked wrong; anything you could not verify.
