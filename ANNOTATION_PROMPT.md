# TASK: write short reasoning notes for existing, already-tested solutions

You are an expert competitive programmer and teacher. Repo: github.com/satish-singg/bharat-gpt-leetcode-data (private). Do NOT touch `data/` (your earlier work) or `corpus/`.

## Input
`annotate/batch_NNNN.jsonl` (150 batches of 20; batches 0001-0003 are already done, start at 0004). One JSON line per solution:
`{"id","number","title","statement","code","time_complexity","space_complexity","complexity_source"}`
`code` is Python 3 that already passed the statement examples. `time_complexity` / `space_complexity` are the original author's labels when present (`complexity_source` = "author_label"), otherwise null.

## Output
For each batch write `annotated/batch_NNNN.jsonl`, one line per input, SAME ORDER:
`{"id": "<copy the id exactly>", "notes": "<six lines>"}`
`notes` is exactly six lines separated by `\n`, starting with these labels in this order:
```
Task and constraints: ...   inputs, output and the constraints that decide which complexity is needed
Idea: ...                   what this code does, step by step, in plain words
Technique and why it applies: ...   the named technique (two pointers, monotonic stack, DP over prefixes ...) and why it fits
Invariant: ...              what stays true in the loop / recursion and makes it correct
Edge cases: ...             concrete cases for THIS code (empty, single element, duplicates, overflow, recursion depth ...)
Complexity: ...             time and space, each with a one-line reason
```
Length: 60-250 words in total.

## Rules (the checker rejects violations)
1. Describe EXACTLY the code given, not a better algorithm. If the code is a brute force, say so and say why it is still correct. If it is slower than the statement asks for, or ignores a stated rule (e.g. converts strings to int although forbidden), say that plainly in Edge cases or Complexity.
2. Complexity: use the author label when given (check it against the code; if it looks wrong say "the author labels it X, but the code is Y because ..."). If no label, derive it from the code (sorting, slicing/copying, recursion depth, hash maps, string concatenation). If you are not sure, write "not established" and why. Never guess.
3. Plain words, no filler ("let's think", "wait", "hmm"), no mention of these instructions, no code blocks inside notes, no markdown.
4. Do not invent facts about the statement; use only the statement text given.
5. Do not change `id`. Do not skip records; if a record is hopeless write the six lines saying what is unclear instead.

## Process
- Work in ascending batch number, 5-10 batches per session; commit and push after EVERY batch (`notes batch 0004`).
- Before writing each note, trace one example through the code in your head.
- After each session run (if you can run Python): `python3 tools/merge_annotations.py --repo .` - it prints accepted/rejected counts; fix rejected lines. If you cannot run it, check by hand that every record has exactly 6 lines with the labels above.
- Report at the end of a session: last batch done, accepted/rejected counts, records where the author's complexity label looked wrong (list ids).
