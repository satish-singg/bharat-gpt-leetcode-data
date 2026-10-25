# Prompt for GitHub Copilot (agent mode): review and repair the ChatGPT-written problems in `newproblems/`

You are a careful competitive-programming problem setter and test engineer. Work ONLY in this repository (`satish-singg/bharat-gpt-leetcode-data`, branch `main`) and ONLY on `newproblems/`, `review/` and `tools/audit_newproblems.py`. Do not touch any other folder.

## What the data is
`newproblems/batch_0001.jsonl` ... `batch_0038.jsonl`: 25 original DSA problems per batch (ids `np-0001` ... `np-0950`), written by ChatGPT. One JSON object per line:
`id, title, difficulty (Easy/Medium/Hard), topic, statement, input_format, output_format, constraints, sample_tests [{stdin, stdout}], reference_python (optimal solution, reads stdin, prints stdout), intended_complexity, brute_force_python (a deliberately simple independent solution)`.
These problems will be used to (1) generate and VERIFY model solutions in Python and Java, so the reference and the tests must be correct, and (2) as training data, so statements must be unambiguous and unique. History: ChatGPT already needed many repair commits (see `git log -- newproblems`), so assume mistakes remain.

## Step 0 - see the current state (run first)
`python3 tools/audit_newproblems.py --report review/np_audit.json`
It runs both programs of every problem on every sample test. Measured before this task: 950 problems, 126 with an issue (samples that disagree with the reference or the brute force, programs that crash with IndentationError / SyntaxError), 94 duplicate titles, and 700 problems whose sample tests use the keys `input`/`output` instead of `stdin`/`stdout`.

## Step 1 - repair, batch by batch (smallest batch number first)
For every problem the audit flags:
1. Find out WHICH part is wrong by reasoning, not by trusting any single file: work the sample by hand from the statement. Cases: (a) both programs agree with each other but not with the expected output -> the expected output is probably wrong; (b) reference and brute force disagree -> one of them is wrong, find the bug; (c) the statement is ambiguous (tie-breaking, 0- vs 1-based, inclusive/exclusive, output order, what to print when no answer) -> rewrite the statement so exactly one answer is possible, then make programs and samples agree with it; (d) a program crashes -> fix the code (indentation/syntax) without changing its algorithm.
2. Fix the smallest thing that is wrong. Keep `id`, `title`, `topic`, `difficulty` unless the title is a duplicate. Never weaken a problem to make a test pass (do not delete a failing sample, do not replace the reference by the brute force).
3. Make every problem have >= 3 sample tests: at least one smallest-valid-input case, one tie / duplicate / all-equal case, one case that distinguishes the optimal from the common wrong approach.
4. Rename sample test keys to `stdin` / `stdout` everywhere.
5. Make titles unique across all batches (the audit prints the duplicates); if two problems are really the same task, keep one and change the other into a clearly different variant, and say so in the log.
6. `constraints` must contain every limit a solver needs (sizes, value ranges, guarantee that an answer exists or what to print otherwise). `intended_complexity` must match the reference.
7. After each batch run `python3 tools/audit_newproblems.py --batch NNNN --verbose`; it must report `with an issue 0` before you commit. Commit once per batch: `Review batch NNNN: <n> problems repaired`. Never report a batch as done while its audit is red.

## Step 2 - differential tests (after Step 1 is green for ALL batches)
For each problem write a tiny random input generator that prints a VALID input for the given `input_format` and `constraints` with SMALL sizes (n <= 8, values <= 20 unless the constraints force more), then run `reference_python` and `brute_force_python` on 200 random inputs and compare. Save generators as `newproblems/gen/np-NNNN.py` and the result as `review/np_differential.jsonl` (`{id, cases, mismatches, first_mismatch_input}`). A mismatch is a bug in the reference, the brute force or the statement: repair it as in Step 1 and rerun. Problems whose input is too complex for a generator: list them in the log, do not guess.

## Rules
- Do not invent facts: if you cannot decide which side is right, leave the problem unchanged and put it in the "unresolved" list.
- Never copy or paraphrase a known LeetCode / Codeforces / HackerRank problem; if a statement looks like a famous problem, list it under "looks derived".
- Do not remove problems and do not renumber ids.
- Write `review/REVIEW_LOG.md`: per batch a table `id | what was wrong (expected / reference / brute force / statement / crash / duplicate title) | what you changed`, then the "unresolved" and "looks derived" lists. Keep it factual, one line per id.
- When finished, post the final audit output (`python3 tools/audit_newproblems.py`) and the counts: repaired, unresolved, looks derived.
