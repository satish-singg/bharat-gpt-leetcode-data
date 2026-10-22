# Batch 0012 — Local Test Report

- Runtime: CPython 3.13.5
- Java compiler/runtime: javac 21.0.12 / Java 21
- Python assertions: 35 passed, 0 failed
- Java 21 assertions: 41 passed, 0 failed
- Total: 76 passed, 0 failed
- Scope: 10 problems, 20 solution records, 20 concept/pitfall Q&A records.
- These are local checks, not official LeetCode judge submissions. Solution status remains pending official/platform evaluation.

| Problem | Python | Java 21 | Result |
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
| **Total** | **35/35** | **41/41** | **PASS** |

Coverage includes cycles and self-cycles, trie prefix vs complete-word checks, wildcard search, sliding-window boundaries, circular robbery cases, duplicate distance constraints, tree inversion, integer boundaries, and bitwise edge cases.

Test-harness correction: the initial Python expectation for target 4 and [1,1,1,1] was wrong; the whole array sums to 4, so the correct minimum length is 4. After correcting the assertion, all 35 Python checks passed. This was a test expectation error, not a solution defect.
