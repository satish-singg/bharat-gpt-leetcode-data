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
