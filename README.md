# Bharat GPT Coding Dataset

A growing dataset of paraphrased coding problems, original Python 3 and Java 21 solutions, reasoning notes, complexity analysis, and DSA concept Q&A.

## Layout
- `data/problems/batch_NNNN.jsonl`: problem metadata, statement, examples/constraints, signatures and public source URL.
- `data/solutions/batch_NNNN.jsonl`: one record per language and approach.
- `data/qa/batch_NNNN.jsonl`: concept questions and prose answers.
- `progress.json`: latest committed progress.
- `skipped.md`: excluded problems and reasons.

## Schemas
Problem: `{"number":1,"title":"Two Sum","slug":"two-sum","difficulty":"Easy","tags":["array","hash_table"],"statement":"Paraphrased statement, examples and constraints","python_signature":"class Solution: ...","java_signature":"class Solution { ...","source_url":"https://github.com/doocs/leetcode/..."}`

Solution: `{"number":1,"title":"Two Sum","language":"python3","approach_id":"hash_map","approach_name":"One-pass hash map","pattern_tags":["array","hash_table"],"notes":"Task and constraints: ...\\nIdea: ...\\nTechnique and why it applies: ...\\nInvariant: ...\\nEdge cases: ...\\nComplexity: ...","code":"...","time_complexity":"O(n) expected","space_complexity":"O(n)","complexity_reason":"...","expected_to_pass_time_limit":true,"self_check":{"ran":false,"examples_passed":0,"examples_total":2},"status":"pending"}`

Q&A: `{"number":3,"kind":"pattern_recognition","question":"How do I recognize the pattern?","answer":"A concrete prose answer.","status":"pending"}`

## Quality
- Every JSONL line must parse as one JSON object.
- Solutions and explanations are written for this dataset; problem statements are paraphrased.
- Status remains `pending` until independently tested. No acceptance or verification is implied.
- `self_check.ran` remains false when examples have not actually been executed.

## Resume
Read `progress.json` and continue with the next ascending problem number. Commit each completed batch and update progress.
