# TASK 5 (continue the dataset): batches 0060 and onward, with the corrected notes rules

Continue exactly as in your original task (ascending problem numbers after 2670, 10 problems / Python 3 + Java 21 / 20 solution records per batch, Q&A, local tests, progress.json). Only these things change - they replace the notes rules of the original task:

1. `language` is `python3` or `java` (not `java21`). `status` is `verified` only if the batch's local tests ran and passed; write the test report `tests/batch_NNNN-test-report.md` in the same commit.
2. `notes` = exactly six lines with the labels `Task and constraints:`, `Idea:`, `Technique and why it applies:`, `Invariant:`, `Edge cases:`, `Complexity:` (60-200 words). The content must be specific to the solution: name its variables and helper methods, the technique and why it fits THIS problem, what stays true in the loop (different from the Idea), 2-3 concrete edge cases and what the code does for them (Java records: int overflow, integer division, recursion depth where they apply), time and space with reasons.
3. Never write anything about tests, local checks, "where permitted", "boundary values are handled as relevant", or any sentence you could paste unchanged into another problem. Every Invariant / Technique / Edge cases line must be unique in the whole dataset.
4. `complexity_reason` is one concrete sentence about this code (what is iterated, sorted, stored), not a template.
5. Several approaches per problem are welcome (brute force + optimal, or two different optimal ones): each approach gets its own record with its own notes; `approach_id` from your existing vocabulary.
6. Before every commit run `python3 tools/validate_notes.py --solutions data/solutions/batch_NNNN.jsonl` - it must print `0 failed`. If it fails, fix the notes, do not commit around it.
7. Keep Q&A as before (2-4 per problem, prose, no code blocks), but each answer must name something concrete from the problem; no answer sentence may appear for two different problems.
8. Never include a problem from `locked/locked_leetcode_numbers.txt` (228 numbers: the held-out evaluation set). Check this list before starting every batch; skip those numbers and record them in skipped.md.
