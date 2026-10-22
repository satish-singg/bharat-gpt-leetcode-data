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
