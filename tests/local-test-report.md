# Local solution test report — initial seed

Date: 2026-10-22 (UTC)

## Environment
- Python: CPython 3.13.5
- Java compiler/runtime: javac 21.0.12 / Java 21
- Tests were run locally using small harnesses with judge-compatible ListNode definitions. These tests are not official LeetCode submissions.

## Results
| Problem | Language | Cases passed | Result |
|---|---|---:|---|
| 1. Two Sum | Python 3 | 4/4 | PASS |
| 1. Two Sum | Java 21 | 4/4 | PASS |
| 2. Add Two Numbers | Python 3 | 4/4 | PASS |
| 2. Add Two Numbers | Java 21 | 4/4 | PASS |
| 3. Longest Substring Without Repeating Characters | Python 3 | 6/6 | PASS |
| 3. Longest Substring Without Repeating Characters | Java 21 | 6/6 | PASS |
| **Total** | **Both languages** | **28/28** | **PASS** |

## Cases covered
- Two Sum: both statement examples, repeated equal values, and a negative-value pair.
- Add Two Numbers: statement example, zero plus zero, unequal lengths with a final carry, and unequal lengths without a final carry.
- Longest Substring: both statement examples, another repeated-character case, empty string, one space, and a case where an old repeated character lies before the current window.

## Status policy
The corresponding solution records set `self_check.ran=true` and record the published examples as passed. The `status` remains `pending`: local tests are not a claim of official acceptance, and the independent evaluation runner has not been run.

## Additional results: problems 4-10

| Problem | Language | Cases passed | Result |
|---|---|---:|---|
| 4. Median of Two Sorted Arrays | Python 3 | 5/5 | PASS |
| 4. Median of Two Sorted Arrays | Java 21 | 5/5 | PASS |
| 5. Longest Palindromic Substring | Python 3 | 5/5 | PASS |
| 5. Longest Palindromic Substring | Java 21 | 5/5 | PASS |
| 6. Zigzag Conversion | Python 3 | 5/5 | PASS |
| 6. Zigzag Conversion | Java 21 | 5/5 | PASS |
| 7. Reverse Integer | Python 3 | 5/5 | PASS |
| 7. Reverse Integer | Java 21 | 5/5 | PASS |
| 8. String to Integer (atoi) | Python 3 | 7/7 | PASS |
| 8. String to Integer (atoi) | Java 21 | 7/7 | PASS |
| 9. Palindrome Number | Python 3 | 5/5 | PASS |
| 9. Palindrome Number | Java 21 | 5/5 | PASS |
| 10. Regular Expression Matching | Python 3 | 6/6 | PASS |
| 10. Regular Expression Matching | Java 21 | 6/6 | PASS |
| **Problems 4-10 total** | **Both languages** | **76/76** | **PASS** |

The Python Zigzag implementation was changed to per-row character lists before this test run, avoiding repeated immutable-string concatenation and matching the stated O(n) time complexity.

## Cumulative totals
- Problems covered so far: 10
- Solution records locally exercised: 20 (10 problems × 2 languages)
- Local test cases passed: 104 (28 for problems 1-3 and 76 for problems 4-10)
- Local test cases failed: 0
- All solution record statuses remain `pending`; these local tests are not official acceptance results.

## Additional results: problems 11-20

| Problem | Language | Cases passed | Result |
|---|---|---:|---|
| 11. Container With Most Water | Python 3 | 4/4 | PASS |
| 11. Container With Most Water | Java 21 | 4/4 | PASS |
| 12. Integer to Roman | Python 3 | 5/5 | PASS |
| 12. Integer to Roman | Java 21 | 5/5 | PASS |
| 13. Roman to Integer | Python 3 | 5/5 | PASS |
| 13. Roman to Integer | Java 21 | 5/5 | PASS |
| 14. Longest Common Prefix | Python 3 | 5/5 | PASS |
| 14. Longest Common Prefix | Java 21 | 5/5 | PASS |
| 15. 3Sum | Python 3 | 3/3 | PASS |
| 15. 3Sum | Java 21 | 3/3 | PASS |
| 16. 3Sum Closest | Python 3 | 3/3 | PASS |
| 16. 3Sum Closest | Java 21 | 3/3 | PASS |
| 17. Letter Combinations of a Phone Number | Python 3 | 3/3 | PASS |
| 17. Letter Combinations of a Phone Number | Java 21 | 3/3 | PASS |
| 18. 4Sum | Python 3 | 3/3 | PASS |
| 18. 4Sum | Java 21 | 3/3 | PASS |
| 19. Remove Nth Node From End of List | Python 3 | 3/3 | PASS |
| 19. Remove Nth Node From End of List | Java 21 | 3/3 | PASS |
| 20. Valid Parentheses | Python 3 | 5/5 | PASS |
| 20. Valid Parentheses | Java 21 | 5/5 | PASS |
| **Problems 11-20 total** | **Both languages** | **78/78** | **PASS** |

The Java 4Sum assertion initially failed because the test harness compared valid quadruplets in different output orders. The solution output was order-independent as required; the test normalization was corrected and all 39 Java assertions for problems 11-20 then passed. No solution change was needed for that test-harness mismatch.

## Batch 0001 cumulative totals (problems 1-20)
- Problem records: 20
- Solution records: 40 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 42 (2–3 per problem)
- Local test cases/assertions passed: 182 (91 Python and 91 Java)
- Local test cases/assertions failed in final runs: 0
- Every solution record has `self_check.ran=true` and records the published statement examples as passed.
- Every solution record still has `status=pending`; local tests are not official LeetCode acceptance results.


# Batch 0002 local tests — problems 21-40

Environment: CPython 3.13.5 and Java 21.0.12. Tests used judge-compatible linked-list node classes where needed. These are local harness results, not official online-judge submissions.

| Range | Language | Cases/assertions passed | Result |
|---|---|---:|---|
| 21-30 | Python 3 | 34/34 | PASS |
| 21-30 | Java 21 | 34/34 | PASS |
| 31-40 | Python 3 | 35/35 plus Sudoku board solve check | PASS |
| 31-40 | Java 21 | 116/116 assertions, including Sudoku cell checks | PASS |
| **Batch 0002 total** | **Both languages** | **219 passing checks** | **PASS** |

Coverage includes linked-list merging and rewiring, parenthesis generation, heap merging, in-place array updates, substring search, bit-shift division including signed overflow, fixed-width sliding windows with repeated words, next permutation, binary search variants, Sudoku validation and solving, run-length encoding, and combination backtracking.

The Java Sudoku assertion count includes per-cell checks that the solved board has no blanks; the final board was also checked against the Sudoku validity rules. A Java substring-concatenation test initially returned valid indices in a different order than the test expected. Since output order is unrestricted, the harness was changed to compare sorted indices; the implementation passed all cases afterward.

## Cumulative totals through problem 40
- Problem records: 40
- Solution records: 80 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 82
- Local tests/assertions passed: 401
- Final-run failures: 0
- All solution records remain `pending` for official/independent evaluation; their local self-checks are marked as run.


# Batch 0003 local tests — problems 41-60

Environment: CPython 3.13.5 and Java 21.0.12. Linked-list harnesses were not needed in this batch. The N-Queens solver outputs were checked for expected solution counts, and the Sudoku/board-oriented cases in prior batches were validated separately.

| Range | Language | Cases/assertions passed | Result |
|---|---|---:|---|
| 41-50 | Python 3 | 35/35 | PASS |
| 41-50 | Java 21 | 34/34 | PASS |
| 51-60 | Python 3 | 33/33 | PASS |
| 51-60 | Java 21 | 33/33 | PASS |
| **Batch 0003 total** | **Both languages** | **135 passing checks** | **PASS** |

Coverage includes in-place index placement, two-pointer water trapping, string multiplication, wildcard DP, greedy jumps, permutation generation with and without duplicates, matrix rotation, anagram grouping, exponentiation by squaring, N-Queens search/counting, Kadane's algorithm, spiral traversals, interval merging/insertion, and factorial-number-system permutation selection.

## Cumulative totals through problem 60
- Problem records: 60
- Solution records: 120 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 122
- Local tests/assertions passed: 536
- Final-run failures: 0
- All solution records remain `pending` for independent/official evaluation; local self-checks are marked as run. Problem 51's statement now includes examples so its self-check fields match the statement.


# Batch 0004 local tests — problems 61-80

Environment: CPython 3.13.5 and Java 21.0.12. Tests included linked-list rotation, DP grids, numeric-string grammar, digit addition, formatting, binary search, stacks, sliding windows, backtracking, matrix transformations, and in-place array compaction.

| Range | Language | Cases/assertions passed | Result |
|---|---|---:|---|
| 61-70 | Python 3 | 37/37 | PASS |
| 61-70 | Java 21 | 37/37 | PASS |
| 71-80 | Python 3 | 36/36 | PASS |
| 71-80 | Java 21 | 36/36 | PASS |
| **Batch 0004 total** | **Both languages** | **146 passing checks** | **PASS** |

The Python and Java test harnesses each ran 73 checks. The combined report splits the checks evenly across the first and second halves for readability. Cases included valid and invalid numeric strings, minimum-window multiplicity, blocked-grid paths, single-row/single-column behavior, matrix zeroing, and duplicate limits.

## Cumulative totals through problem 80
- Problem records: 80
- Solution records: 160 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 162
- Local tests/assertions passed: 682
- Final-run failures: 0
- Every solution record remains `pending` for independent/official evaluation; local self-checks are marked as run.


# Batch 0005 local tests — problems 81-100

Environment: CPython 3.13.5 and Java 21.0.12. Tests included duplicate-aware rotated search, linked-list duplicate removal and partitioning, monotonic-stack histogram/rectangle algorithms, scramble-string memoization, array merging, Gray code, subset generation, decoding DP, linked-list segment reversal, IP-address backtracking, tree traversals/generation/validation/recovery, and interleaving DP.

| Language | Cases/assertions passed | Result |
|---|---:|---|
| Python 3 | 63/63 | PASS |
| Java 21 | 63/63 | PASS |
| **Batch 0005 total** | **126 passing checks** | **PASS** |

Tree tests include inorder traversal, unique-BST counts, strict BST-bound validation (including duplicate values), recovering two swapped values, and structural tree equality. Scramble String was tested on positive and negative examples; histogram and maximal-rectangle cases included empty-height and single-cell boundaries.

## Cumulative totals through problem 100
- Problem records: 100
- Solution records: 200 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 202
- Local tests/assertions passed: 808
- Final-run failures: 0
- Every solution record remains `pending` for independent/official evaluation; local self-checks are marked as run.


# Batch 0006 local tests — problems 101-120

Environment: CPython 3.13.5 and Java 21.0.12. The batch exercises tree mirroring, BFS traversals, reconstruction from traversal arrays, balanced BST construction, tree depth and path sums, in-place flattening, subsequence DP, next-pointer population, Pascal rows, and triangle DP.

| Language | Cases/assertions passed | Result |
|---|---:|---|
| Python 3 | 41/41 | PASS |
| Java 21 | 28/28 | PASS |
| **Batch 0006 total** | **69 passing checks** | **PASS** |

Tree checks verify reconstructed preorder/inorder results, BST ordering and balance, path-sum root-to-leaf behavior, flattened preorder with all left pointers null, and next pointers across both perfect and sparse trees. The Java harness groups several related checks into combined assertions, so its assertion count is lower than the Python case count.

## Cumulative totals through problem 120
- Problem records: 120
- Solution records: 240 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 242
- Local tests/assertions passed: 877
- Final-run failures: 0
- Every solution record remains `pending` for independent/official evaluation; local self-checks are marked as run.


# Batch 0007 local tests — problems 121-140

Environment: CPython 3.13.5 and Java 21.0.12. Tests cover one- and two-transaction stock profit, tree path sums, filtered palindromes, shortest word ladders (including all shortest paths), integer-limit consecutive sequences, flood fill, palindrome partitioning, graph cloning, greedy station/candy allocation, bitwise uniqueness, random-pointer list copying, and word-break DP/backtracking.

| Language | Cases/assertions passed | Result |
|---|---:|---|
| Python 3 | 53/53 | PASS |
| Java 21 | 21/21 combined assertions | PASS |
| **Batch 0007 total** | **74 passing checks** | **PASS** |

The Java checks group several examples into combined assertions. The Longest Consecutive Sequence tests include both integer extremes to verify that predecessor/successor arithmetic does not overflow. Graph-copy tests verify that clones are distinct objects and that cyclic neighbor/random-pointer relationships point to cloned nodes.

## Cumulative totals through problem 140
- Problem records: 140
- Solution records: 280 (Python 3 and Java 21 for each problem)
- Concept Q&A records: 282
- Local tests/assertions passed: 951
- Final-run failures: 0
- Every solution record remains `pending` for independent/official evaluation; local self-checks are marked as run.


# Batch 0008 local tests — problems 141-160

The batch's Python algorithm harness ran under CPython 3.13.5: **27/27 assertions passed**. The Java 21 algorithm harness compiled with OpenJDK 21.0.12.1 and passed **25/25 assertions**. The checks covered linked-list cycle detection and entry, list reordering and sorting, tree traversals/upside-down rewiring, LRU/Min Stack behavior, line-slope normalization including vertical lines and duplicate points, RPN negative division, word reversal/whitespace, max-product arrays, rotated-array minima with duplicates, read4 single and repeated reads, sliding-window strings, and shared-node intersection.

The read4 checks use a simulated reader implementing the judge-provided `read4` contract. These are local smoke tests, not official LeetCode judge results. All 40 solution records are marked locally exercised, while their evaluation status remains `pending` pending broader randomized/official validation.

| Language | Checks passed | Result |
|---|---:|---|
| Python 3 | 27/27 | PASS |
| Java 21 | 25/25 | PASS |
| **Batch 0008 total** | **52/52** | **PASS** |

## Batch 0009 — problems 161–170

- Added 10 problem records, 20 Python 3 / Java 21 solution records, and 20 concept/pitfall Q&A records.
- JSONL structure and record counts validated: 10 problem records, 20 solution records, and 20 Q&A records; every line parsed as JSON.
- **Execution status:** the batch's solution snippets have not yet been run in local language harnesses. Their `self_check.ran` flags are therefore false, and records remain `pending`. No claim of official LeetCode acceptance is made.

## Batch 0011 — problems 191, 198–206

- Python 3 local harness: 35 assertions passed, 0 failed.
- Java 21 compiled local harness: 21 assertions passed, 0 failed.
- Total added local checks: 56.
- Cumulative total recorded in `progress.json`: 1,193 passed, 0 failed.
- SQL/shell-only problems 192–197 were skipped. These checks are not official LeetCode judge results.



# Batch 0012 local tests — problems 207, 208, 209, 211, 213, 217, 219, 226, 228, 231

Environment: CPython 3.13.5 and OpenJDK/javac 21.0.12.

| Problem | Python checks | Java 21 checks | Result |
|---|---:|---:|---|
| 207 Course Schedule | 4/4 | 4/4 | PASS |
| 208 Implement Trie | 2/2 | 4/4 | PASS |
| 209 Minimum Size Subarray Sum | 4/4 | 5/5 | PASS |
| 211 WordDictionary | 2/2 | 5/5 | PASS |
| 213 House Robber II | 4/4 | 4/4 | PASS |
| 217 Contains Duplicate | 3/3 | 3/3 | PASS |
| 219 Contains Duplicate II | 4/4 | 4/4 | PASS |
| 226 Invert Binary Tree | 3/3 | 3/3 | PASS |
| 228 Summary Ranges | 4/4 | 4/4 | PASS |
| 231 Power of Two | 5/5 | 5/5 | PASS |
| **Batch 0012 total** | **35/35** | **41/41** | **PASS** |

A first Python test expectation was corrected: target 4 with [1,1,1,1] has a valid length-4 window. Final results: 35 Python assertions passed, 0 failed; 41 Java 21 assertions passed, 0 failed. These are local harness results, not official LeetCode judge results.

## Updated cumulative totals through batch 0012
- Problem records: 200
- Solution records: 400 (Python 3 and Java 21 for each problem)
- Concept/pitfall Q&A records: 402
- Local test assertions passed: 1269
- Local test assertions failed in final runs: 0
- Solution statuses remain pending official/platform evaluation.

## Batch 0013 — 2026-10-22
- Python 3: 41 assertions passed, 0 failed.
- Java 21: 41 assertions passed, 0 failed (compiled with javac 21.0.12.1).
- Batch total: 82 passed, 0 failed.
- Cumulative recorded checks: 1,351 passed, 0 failed.
- Local harness checks only; not official LeetCode judge submissions.

## Batch 0014 — 2026-10-23
- Problems: 301, 303, 304, 306, 307, 309, 310, 312, 313, 315.
- Python 3 spot tests: 34 passed, 0 failed.
- Java 21 spot tests: 25 passed, 0 failed; compiled with javac 21.0.12.1.
- Total recorded cases: 59 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- These are local algorithm checks, not official LeetCode submissions; solution statuses remain pending.

## Batch 0015 — 2026-10-23
- Problems: 316, 318, 319, 322, 326, 328, 329, 331, 332, 334.
- Python 3 spot tests: 29 passed, 0 failed.
- Java 21 spot tests: 29 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 58 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0016 — 2026-10-23
- Problems: 337, 338, 341, 342, 343, 344, 345, 347, 349, 350.
- Python 3 spot tests: 24 passed, 0 failed.
- Java 21 spot tests: 22 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 46 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0017 — 2026-10-23
- Problems: 354, 357, 368, 376, 377, 378, 380, 381, 383, 386.
- Python 3 spot tests: 26 passed, 0 failed.
- Java 21 spot tests: 26 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 52 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0018 — 2026-10-23
- Problems: 387, 388, 389, 390, 392, 393, 394, 395, 396, 397.
- Python 3 spot tests: 29 passed, 0 failed.
- Java 21 spot tests: 29 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 58 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0019 — 2026-10-23
- Problems: 399, 400, 401, 402, 403, 404, 405, 406, 407, 409.
- Python 3 spot tests: 27 passed, 0 failed.
- Java 21 spot tests: 27 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 54 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0020 — 2026-10-23
- Problems: 410, 412, 413, 414, 415, 416, 417, 419, 421, 423.
- Python 3 spot tests: 27 passed, 0 failed.
- Java 21 spot tests: 26 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 53 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0021 — 2026-10-23
- Problems: 424, 427, 429, 430, 433, 435, 437, 438, 440, 441.
- Python 3 spot tests: 22 passed, 0 failed.
- Java 21 spot tests: 22 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 44 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0022 — 2026-10-23
- Problems: 442, 443, 445, 446, 448, 450, 451, 452, 453, 454.
- Python 3 spot tests: 15 passed, 0 failed.
- Java 21 spot tests: 15 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 30 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0023 — 2026-10-23
- Problems: 455, 456, 457, 459, 461, 462, 463, 464, 467, 468.
- Python 3 spot tests: 29 passed, 0 failed.
- Java 21 spot tests: 29 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 58 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Batch 0024 — 2026-10-23
- Problems: 470, 473, 474, 475, 476, 477, 478, 482, 485, 486.
- Python 3 spot tests: 26 passed, 0 failed.
- Java 21 spot tests: 26 passed, 0 failed; compiled with javac 21.0.12.1.
- Total: 52 passed, 0 failed.
- JSONL verified after fetching from GitHub: 10 problem records, 20 solution records, 20 Q&A records.
- Local checks are not official LeetCode submissions; solution statuses remain pending.

## Targeted verification — Batch 0025, problem 504 (Base 7)

Date: 2026-10-23 (UTC)

- Environment: CPython 3.13.5; javac/java 21.0.12.1.
- Python 3: 5/5 local assertions passed: 100, -7, 0, -1000, and 49.
- Java 21: compiled successfully; 7/7 local assertions passed: the same five values plus Integer.MIN_VALUE and Integer.MAX_VALUE.
- Both solution records in `data/solutions/batch_0025.jsonl` now have `self_check.ran=true` and the executed case counts. Status remains `pending` because local execution does not establish official LeetCode acceptance.
- This is a targeted check only; it does not mean Batch 0025 or the overall task is complete.
