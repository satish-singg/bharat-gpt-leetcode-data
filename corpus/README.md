# corpus/ - solutions mined from public GitHub repos (built by Claude, 2026-10-22; separate from the ChatGPT-written `data/`)

Both builds already EXCLUDE the 228 locked evaluation problems in `locked/locked_leetcode_numbers.txt` (newfacade/LeetCodeDataset v0.3.1 test split).
Rebuild: `python3 tools/build_leetcode_corpus.py ...` and `python3 tools/build_doocs_corpus.py ...` (see the docstrings; needs local clones of the source repos).

| folder | sources (licence) | content |
|---|---|---|
| `anas_kamyu/` | AnasImloul/Leetcode-Solutions (Unlicense), kamyu104/LeetCode-Solutions (MIT) | 1,809 problems; Python 3 (kamyu py2 converted), C++, Java; several approaches per problem; author `Time:`/`Space:` headers as complexity labels |
| `doocs_huajianmao/` | doocs/leetcode (CC BY-SA 4.0), huajianmao/leetcode branch `hjmao` (no licence file; Java) | 3,859 problems; per "Solution N: <approach title>" a written explanation, a short Thinking note (idea / bottleneck / pitfall), complexity in prose, code in up to 14 languages |

Files per folder: `problems.jsonl`, `solutions.jsonl.gz` (every record, with tier and example results), `sft.jsonl.gz` (chat records, tier A/B/C), `report.json` (counts).
Tiers: A = complexity label (+ explanation for doocs) and every runnable statement example passed; B = examples passed; C = no runnable example (all non-Python languages, tree/list problems); D = an example failed (in solutions, not in sft). Python only is executed; examples are a weak check, not hidden tests.
`status` of everything is still unverified by an independent runner. Records keep their `source` and `license` fields.
