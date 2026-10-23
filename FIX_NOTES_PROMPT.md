# TASK 4: replace the weak reasoning notes in your own dataset (and fix status)  -  repo bharat-gpt-leetcode-data

You did very good work on the code, the tests and the Q&A: local tests 5,683 passed / 0 failed, no duplicates, no locked problems. The ONE thing that is not good enough is the `notes` field after batch 0003.
This model will be trained to reason from these notes, so each note must be about THIS solution, not a template.

## What is wrong (measured on batches 0004-0059)
- 52% of the records share one of a few generic Edge-cases sentences ("Check empty or singleton inputs where permitted, boundaries, and minimal structures." appears 260 times).
- 76% use one of only 160 Technique lines; 22% reuse a generic Invariant ("The maintained accumulator, stack, DP state, sorted ordering ... preserve the information required ...").
- Many notes are not the six labelled lines (they start with "Task:" and drop "Technique and why it applies"), some Invariants repeat the Idea, some Edge cases talk about the tests ("Six local tests include ...").
- `complexity_reason` is also a template ("Each input element or state is processed a bounded number of times ...").
- `status` is "pending" for batches 0001-0024.
- the language label is "java" in some batches and "java21" in others.

## Part A: rewrite the notes of the existing solutions
Input: `fixnotes/in/batch_NNNN.jsonl` (56 files, 1,054 records; ids like `171:python3:base_26`). Each line has the statement, the approach, the code and the complexity labels.
Output: `fixnotes/out/batch_NNNN.jsonl`, SAME FILE NAME, one line per input line, SAME ORDER:
`{"id": "<copy exactly>", "notes": "<six lines>", "complexity_reason": "<one specific sentence>"}`

`notes` = exactly six lines separated by \n, in this order, each starting with its label:
```
Task and constraints: inputs, output, and the constraint that decides the needed complexity (e.g. n up to 1e5 -> need O(n log n) or better)
Idea: what THIS code does, step by step, in plain words, naming its variables / helper methods
Technique and why it applies: the named technique (hash map for complements, monotonic stack, DP over prefixes ...) and the reason it fits THIS problem
Invariant: what stays true in the loop / recursion and makes it correct; it must say something DIFFERENT from the Idea line
Edge cases: 2-3 concrete cases for this code and what happens (empty list, one node, duplicates, negative numbers, int overflow in Java, recursion depth, k larger than n ...)
Complexity: time and space with one-line reasons, consistent with the code and the given labels
```
60-200 words. The Java record of a problem may reuse the Idea and Technique of the Python record when the algorithm is identical, but its Edge cases must mention Java-specific points (int overflow, integer division, array indexing, StringBuilder, recursion depth) where they apply, and its Invariant/Edge cases must still describe the Java code.

Rules:
1. Read the code and trace ONE example before writing. Describe exactly this code, not a better algorithm.
2. Never write: "Six local tests...", "where permitted", "maintained accumulator", "minimal structures", "relevant boundaries", anything about tests, self-checks, your instructions, "wait", "hmm", markdown, code blocks.
3. Do not reuse a Technique / Invariant / Edge cases line for a different problem. Each problem gets its own sentences.
4. `complexity_reason`: ONE sentence naming what is iterated / sorted / stored (e.g. "One pass over nums, each step does a dict lookup and insert, and the dict holds at most n entries.").
5. If the code looks wrong for the statement, write the notes anyway but put the bug plainly in Edge cases, and list the id in your session report.

## Part B: re-do and verify annotation notes
Input `fixnotes/redo_annotations_in.jsonl` (69 records, same format as `annotate/batch_*.jsonl`; `code` is Python 3 from another repo). Write `fixnotes/redo_annotations_out.jsonl` with `{"id","notes"}` in the same ORDER (six lines, same rules, no complexity_reason).
These were rejected by the checker or the old note said the code is wrong. For each: RUN the code against the statement examples and a small brute force. If the code is correct, write a normal note. If it really is wrong, do not write notes; write `{"id": "...", "flag": "<one sentence: input where it fails and what it returns>"}`. (One of them, `342:kamyu104:3` Power of Four, is probably correct - the old note called it wrong. Check it.)

## Part C: check (you have no shell, so the repo checks for you)
You write only `fixnotes/out/batch_NNNN.jsonl` and `fixnotes/redo_annotations_out.jsonl`; do NOT edit `data/` for this task (the owner runs `tools/apply_notes_fix.py`, which writes the notes into `data/solutions/`, sets `verified` for batches 0010-0024 and unifies `java21` -> `java`).
Every push triggers the GitHub Action `validate-notes` (file `.github/workflows/validate-notes.yml`, runs `tools/validate_notes.py`). After each push open the run for your commit (Actions tab, or the commit status): it must be green. If it is red, the log lists each failing id and the reason (`FAIL batch_0004.jsonl 71:python3 | ...`): rewrite exactly those lines and push again. Never report a batch as done while its check is red.
If you CAN run Python yourself (your own sandbox with the files from the repo), also run `python3 tools/validate_notes.py --in fixnotes/in --out fixnotes/out` before pushing - it is the same check.
Batches 0004-0009 and the rest of 0001-0003 have no local test report: run local tests for them in your sandbox (Python 3 and Java 21 as before) and save `tests/batch_NNNN-test-report.md` in the same table format as batch 0010 (tests only; changing status is done by the apply script).

## Process
- `git pull --rebase` (or re-read the latest repo state through the connector) before every push, so you never overwrite files.
- Work in ascending batch order, 5-8 batches per session, one commit per batch (`fix notes batch 0004`).
- Do not change anything in `data/`, `corpus/`, `annotate/`, `annotated/` for this task.
- End of every session report: last batch done, the result of the `validate-notes` run for your last commit (green/red and the failure count), ids where the code looked wrong, anything you could not verify. Do not claim a result you did not see.
