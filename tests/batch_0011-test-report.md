# Batch 0011 — Local Test Report

- Runtime: CPython 3.13.5
- Runtime/compiler: OpenJDK / javac 21.0.12.1
- Python harness: 35 assertions passed, 0 failed
- Java 21 compiled harness: 21 assertions passed, 0 failed
- Scope: Problems 191, 198–206; 10 problems, 20 solution records, 20 concept/pitfall Q&A records.
- SQL/shell-only problems 192–197 were skipped to keep this corpus focused on Python 3 and Java 21 algorithm solutions.
- These are local algorithm harness checks, not official LeetCode judge submissions. The solution records remain marked pending official/platform evaluation.

## Coverage

| Problem | Python checks | Java checks |
|---|---:|---:|
| 191 Number of 1 Bits | 4 | 2 |
| 198 House Robber | 4 | 2 |
| 199 Binary Tree Right Side View | 2 | 2 |
| 200 Number of Islands | 3 | 2 |
| 201 Bitwise AND of Numbers Range | 4 | 2 |
| 202 Happy Number | 5 | 2 |
| 203 Remove Linked List Elements | 2 | 2 |
| 204 Count Primes | 4 | 2 |
| 205 Isomorphic Strings | 5 | 3 |
| 206 Reverse Linked List | 2 | 2 |

The Python implementations were executed against a local assertion harness. The Java 21 algorithm equivalents were compiled and executed against a local harness. Both passed all listed assertions.
