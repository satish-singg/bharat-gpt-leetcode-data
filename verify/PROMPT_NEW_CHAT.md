# Paste this into a NEW ChatGPT chat (verify batch 1). For batch K, replace 1 by K in the file names.

You are a careful test engineer working in my GitHub repo.
Repo: https://github.com/satish-singg/bharat-gpt-leetcode-data  (private, branch main). Work ONLY on these paths:
  input : verify/pending_1_of_6.jsonl   (100 lines, one JSON object per solution)
  output: verify/results/pending_1_of_6.results.jsonl   (you create it; one JSON line per input line, same order)
Do not touch any other file.

Each input line: {"id","title","difficulty","language","statement","signature","code"}. language is python3 or java. code is a LeetCode-style class Solution; call the method that is in the code (signature may be null).

STEP 0 (environment). Execute, in your code sandbox: python3 --version ; javac -version ; java -version. Show me the real output. If a command cannot run, say exactly which one and stop. Then read verify/pending_1_of_6.jsonl from the repo and tell me the number of lines (must be 100) and the first id. If you cannot read the file, say FILE NOT FOUND and stop.

Then work in chunks of 10 lines (lines 1-10, 11-20, ... 91-100). Finish ONE chunk completely before the next:
  a. Run each solution on every example in its statement (Input/Output).
  b. Write an independent brute-force/reference solution yourself (simple, obviously correct, small sizes) and compare with the record's code on at least 200 random small inputs that respect the constraints (include empty/minimum size, one element, duplicates, negatives, large values for Java overflow). If several answers are valid, use a validity checker, not equality. Build linked lists/trees from arrays in your harness.
  c. Run one maximum-size input from the constraints; record whether it finishes within 2 s (Python) / 1 s (Java).
  d. Java: compile with javac 21 and run; report compile errors.
  e. Append the 10 result lines to verify/results/pending_1_of_6.results.jsonl and COMMIT AND PUSH to main (message: "verify batch 1 lines N-M"). Show me the commit hash and the 10 result lines. Only then start the next chunk.

Result line format (JSON only, no prose):
{"id":"<copy>","examples":"pass|fail|error","random_tests":<n run>,"random":"pass|fail|error|not_run","max_size":"ok|slow|error|not_run","compiled":true|false|null,"verdict":"pass|fail|unclear","failing_input":"<only if fail: input, code's output, expected output>","note":"<one short sentence if verdict is not pass>"}

Rules: verdict is pass only if examples pass AND random tests pass AND max-size is not slow. Never write pass for a record you did not execute: if you could not run it, write verdict unclear and explain. Test the Python and Java record of the same problem separately. After the last chunk, print one final line {"executed": n, "of": 100} and the counts of pass / fail / unclear.
