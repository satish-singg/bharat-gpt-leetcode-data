# Verification prompt (paste this together with ONE file verify/pending_K_of_6.jsonl, K = 1..6)

You are a careful test engineer. The attached file has 100 lines, one JSON object per solution:
{"id","title","difficulty","language","statement","signature","code"}. `language` is `python3` or `java`. `code` is a LeetCode-style solution (class Solution with a method; use the method signature that is in `code`; `signature` may be null).

The file is named in the request (read it from the repo, or from the attachment). If you cannot read it reply only: FILE NOT FOUND.
You MUST actually execute code (a real Python 3 / Java 21 sandbox). If you cannot execute code at all, reply only: NO EXECUTION. Do not guess and do not verify by reading.
Work in chunks of 25 lines and write the results to verify/results/<file stem>.results.jsonl in the repo.

For EVERY record:
1. Run the code on every example in `statement` (Input/Output). 
2. Write an independent brute-force or reference solution yourself (simple and obviously correct, small sizes) and compare it with the record's code on at least 200 random small inputs that respect the constraints in `statement`, including the edge cases (empty or minimum size, one element, duplicates, negative numbers, maximum values for overflow in Java). For problems with several valid answers compare with a validity checker, not equality. For problems with linked lists or trees, build them from arrays in your harness.
3. Run one maximum-size input from the constraints and record whether it finishes within 2 seconds (Python) / 1 second (Java).
4. For Java: compile with javac 21 and run; report compile errors.

Output: ONE JSON object per input line, same order, nothing else (no prose, no markdown):
{"id": "<copy>", "examples": "pass|fail|error", "random_tests": <number of cases run>, "random": "pass|fail|error|not_run", "max_size": "ok|slow|error|not_run", "compiled": true|false|null, "verdict": "pass|fail|unclear", "failing_input": "<only if fail: the input, the code's output, the expected output>", "note": "<one short sentence if verdict is not pass>"}

Rules: verdict is `pass` only if examples pass AND random tests pass AND the max-size run is not slow. Never write `pass` for a record you did not run. If two records share a problem, test them separately. If the statement is too ambiguous to test, use `unclear` and say why. Report honestly how many records you really executed at the end as a final line: {"executed": <n>, "of": 100}.
