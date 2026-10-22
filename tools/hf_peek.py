"""Schema peek for HF datasets whose columns we do not know yet (run before java_pilot's hf:REPO:FIELD).
For each spec `REPO[:CONFIG][@SPLIT]` streams N rows and prints columns, value types/lengths and a truncated first-row preview.
   env -u PYTHONPATH python tools/hf_peek.py --out peek.json PipableAI/pip-txt-to-sql-spider-bird-dataset livebench/coding@test
Nothing is downloaded beyond the first rows; no field names needed."""
import argparse, json, os, sys


def describe(value, cut=300):
    if isinstance(value, str):
        return {"type": "str", "chars": len(value), "head": value[:cut]}
    if isinstance(value, (list, tuple)):
        return {"type": "list", "len": len(value), "first": describe(value[0], cut) if value else None}
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(value)[:20]}
    return {"type": type(value).__name__, "value": value if isinstance(value, (int, float, bool)) or value is None else str(value)[:cut]}


def parse_spec(spec):
    repo_cfg, _, split = spec.partition("@")
    repo, _, cfg = repo_cfg.partition(":")
    return repo, (cfg or None), (split or None)


def peek_rows(rows, n):
    out = []
    for r in rows:
        out.append({k: describe(v) for k, v in r.items()})
        if len(out) >= n:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+"); ap.add_argument("--rows", type=int, default=2); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from datasets import load_dataset
    rep = {}
    for spec in a.specs:
        repo, cfg, split = parse_spec(spec)
        tried = [split] if split else ["train", "test", "validation"]
        for sp in tried:
            try:
                kw = {"name": cfg} if cfg else {}
                rows = peek_rows(load_dataset(repo, split=sp, streaming=True, **kw), a.rows)
                rep[spec] = {"split": sp, "rows": rows}
                print("==", spec, "split", sp, "columns:", list(rows[0]) if rows else [])
                for k, v in (rows[0].items() if rows else []):
                    print("  ", k, json.dumps(v)[:400])
                break
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt): raise
                rep[spec] = {"error": f"{type(e).__name__}: ...{str(e)[-400:]}"}
        if "error" in rep[spec]:
            print("==", spec, "ERROR", rep[spec]["error"])
    json.dump(rep, open(os.path.expanduser(a.out), "w"), indent=1)
    print("saved", a.out)


if __name__ == "__main__":
    main()
