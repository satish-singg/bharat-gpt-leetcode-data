# Batch 0013 Local Test Report

Date: 2026-10-22

## Coverage
Problems: 235, 236, 238, 239, 240, 242, 268, 287, 295, and 300.
Languages: Python 3 and Java 21.

## Results
- Python 3: 41 assertions passed, 0 failed.
- Java 21: compiled with javac 21.0.12.1; 41 assertions passed, 0 failed.
- Total: 82 assertions passed, 0 failed.

Coverage included BST and binary-tree LCA identity cases; arrays with zeros and negative values; sliding-window boundaries and equal values; empty and singleton matrix searches; anagram length/frequency mismatches; missing values at boundaries; duplicate distributions; median after odd/even inserts and integer extremes; and increasing, decreasing, duplicate-only, and empty LIS inputs.

These are local harness checks of the algorithms, not official LeetCode judge submissions. The solution records remain pending official/platform evaluation. Tree-based Java methods rely on the standard judge-provided TreeNode definition; the anagram implementation assumes lowercase English letters, matching the problem constraints.
