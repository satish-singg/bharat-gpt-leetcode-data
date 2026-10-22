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
