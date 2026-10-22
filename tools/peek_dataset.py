#!/usr/bin/env python3
"""Download ONE file of a Hugging Face dataset and print its real columns and one example row, before any adapter is trusted.
  python3 tools/peek_dataset.py newfacade/LeetCodeDataset LeetCodeDataset-test.jsonl
  python3 tools/peek_dataset.py BAAI/TACO ALL/test-00000-of-00001.parquet
  python3 tools/peek_dataset.py deepmind/code_contests data/test-00000-of-00001-9c49eeff30aacaa8.parquet
Needs HF_TOKEN only for gated sets. Prints at most 400 characters per field."""
import json, sys
from huggingface_hub import hf_hub_download
repo, fn = sys.argv[1], sys.argv[2]
p = hf_hub_download(repo, fn, repo_type="dataset")
if fn.endswith(".parquet"):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(p); print("rows:", pf.metadata.num_rows); print("schema:", pf.schema_arrow)
    row = next(pf.iter_batches(batch_size=1)).to_pylist()[0]
else:
    n = sum(1 for _ in open(p, encoding="utf-8")); print("rows:", n)
    row = json.loads(open(p, encoding="utf-8").readline())
print("columns:", list(row))
for k, v in row.items():
    print(f"--- {k} ({type(v).__name__}):", str(v)[:400].replace("\n", "\\n"))
