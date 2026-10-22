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

## unified/ (same schema as ChatGPT's `data/solutions`)
`python3 tools/unify_corpus.py --repo . --locked locked/locked_leetcode_numbers.txt` merges ChatGPT's `data/` and both mined builds into ONE solution schema (number,title,language,approach_id,approach_name,pattern_tags,notes,code,time/space_complexity,complexity_reason,expected_to_pass_time_limit,self_check,status + `think`, `explanation`, `tier`, `source`, `license`) and renders chats:
- `sft_plain.jsonl.gz` - answer only: `**Approach: ...**`, explanation (doocs), code, complexity line.
- `sft_think.jsonl.gz` - the same with `<think>\n note \n</think>` first. Note = ChatGPT's six-line `notes`, or doocs' "Thinking" block (idea / bottleneck / pitfall, ~55 words). Use in the decay stage and SFT only (see docs/FINAL_PLAN.md); keep sft_plain for the no-notes inference path / A-B arms.
- `qa_sft.jsonl.gz` - ChatGPT's concept Q&A as chats. `solutions.jsonl.gz`, `problems.jsonl.gz` hold all records (tier D kept there, not in the chats).
`approach_id` of mined records is a keyword heuristic (`approach_id_source`). Tiers: A/B/C/D as above (Java now executed too, for simple types); T = ChatGPT record that ran its own examples, U = not run.

## annotate/
2,995 kamyu/Anas Python solutions that passed the examples but have no written note, in batches of 20 for a teacher model. Reply format `{"id","notes"}` (six labelled lines) into `annotated/*.jsonl`; `tools/merge_annotations.py` validates them, then rerun `unify_corpus.py` - the notes appear as `think`/`notes` and in sft_think.
