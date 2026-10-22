#!/usr/bin/env python3
"""How much do the candidate Java sources overlap each other and the Java already in cs-v5? CPU only, read-only.

  python3 tools/java_overlap.py --cs-train ~/cs-data/cs-v5/clean/train.jsonl --out ~/java_overlap.json \
      --sources stack_java_clean:ALL,java_code_large:20000,starcoderdata:20000

NAME:ALL hashes the whole source (needed as a reference set; stack_java_clean is 2.56 GB)
Sampled sources (NAME:N) are read in shuffled order (fixed seed), not from the head. Use --cache FILE so the slow cs-v5 pass runs once.. NAME:N hashes only the first N rows.
Overlap of a source against a reference is only trustworthy when the REFERENCE is complete (cs_v5 Java and every NAME:ALL source are):
the report says "x% of this source's sampled files also exist in <reference>". Two sampled sources are never compared with each other.
Two fingerprints per file: exact (whitespace-normalised text) and body (comments removed too, so a different license header does not hide a copy).
cs-v5 Java = rows of train.jsonl with source code_java_sql_js whose prov.path ends in .java. Needs the same pilot-venv2 as java_pilot.py (datasets).
"""
import argparse, hashlib, json, os, pickle, re, sys, time

COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)                # Java (also fine for C-like languages)
COMMENTS = {"java": COMMENT, "python": re.compile(r"#[^\n]*")}      # Python: # comments only (docstrings are content and stay)


def fingerprints(text, lang="java"):
    flat = " ".join(text.split())
    body = " ".join(COMMENTS[lang].sub(" ", text).split())
    h = lambda s: int(hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()[:16], 16)
    return h(flat), h(body)


def build_sets(texts, limit=None, lang="java"):
    ex, bd, n = set(), set(), 0
    for t in texts:
        if limit is not None and n >= limit: break
        if not t: continue
        a, b = fingerprints(t, lang); ex.add(a); bd.add(b); n += 1
    return {"exact": ex, "body": bd, "files": n}


def overlap(texts, ref, limit=None, lang="java"):
    """fraction of this source's files whose fingerprint is in the reference (the source's own duplicates are counted once each)."""
    n = hit_e = hit_b = 0
    for t in texts:
        if limit is not None and n >= limit: break
        if not t: continue
        a, b = fingerprints(t, lang); n += 1
        hit_e += a in ref["exact"]; hit_b += b in ref["body"]
    return {"files": n, "in_ref_exact": round(hit_e / n, 4) if n else None, "in_ref_body": round(hit_b / n, 4) if n else None}


def iter_cs_java(path, progress=False, source="code_java_sql_js", ext=".java"):
    marker = '"%s"' % source
    found = 0
    with open(os.path.expanduser(path), encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if progress and i % 100000 == 0:
                print(f"  cs-v5: {i:,} lines read, {found:,} matching files so far", file=sys.stderr, flush=True)
            if marker not in line: continue
            try: d = json.loads(line)
            except ValueError: continue
            if d.get("source") == source and str((d.get("prov") or {}).get("path", "")).endswith(ext):
                found += 1
                yield d.get("text")


def stream_source(name, shuffle=False):
    if name.startswith("jsonl:"):                       # jsonl:PATH  (a file with a "text" field per line, e.g. swh_fetch_pilot.py --save-jsonl)
        def rows():
            with open(os.path.expanduser(name[6:]), encoding="utf-8") as f:
                for line in f:
                    if line.strip(): yield json.loads(line).get("text")
        return rows()
    """shuffle=True: shuffled shard order + a 10,000-row buffer with a fixed seed, so a sample is not just the head of the first shard."""
    from datasets import load_dataset
    kw = {"stack_java_clean": (("ammarnasr/the-stack-java-clean",), {}, "content"), "java_code_large": (("ajibawa-2023/Java-Code-Large",), {}, "code"),
          "starcoderdata": (("bigcode/starcoderdata",), {"data_dir": "java"}, "content")}
    if name not in kw: raise SystemExit("unknown source " + name)
    args, extra, field = kw[name]
    ds = load_dataset(*args, split="train", streaming=True, **extra)
    if shuffle: ds = ds.shuffle(seed=0, buffer_size=10000)
    return (r.get(field) for r in ds)


def parse_item(item):
    """'stack_java_clean:ALL' -> (name, None); 'x:5000' -> (x, 5000); 'jsonl:/p/f.jsonl:2000' -> ('jsonl:/p/f.jsonl', 2000); no suffix -> 20000."""
    item = item.strip()
    m = re.match(r"^(.*?):(ALL|all|\d+)$", item)
    if not m: return item, 20000
    return m.group(1), None if m.group(2).upper() == "ALL" else int(m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cs-train", required=True); ap.add_argument("--out", required=True); ap.add_argument("--sources", required=True)
    ap.add_argument("--lang", default="java", choices=sorted(COMMENTS), help="java (default) or python: picks the comment syntax and the cs-v5 source/extension")
    ap.add_argument("--cache", help="pickle of the cs-v5 fingerprints: built once (reads the whole ~10 GB train.jsonl, several minutes), reused after")
    a = ap.parse_args()
    t0 = time.time()
    cache = os.path.expanduser(a.cache) if a.cache else None
    if cache and os.path.exists(cache):
        refs = {"cs_v5": pickle.load(open(cache, "rb"))}
    else:
        src, ext = ("code_java_sql_js", ".java") if a.lang == "java" else ("code_python", ".py")
        refs = {"cs_v5": build_sets(iter_cs_java(a.cs_train, progress=True, source=src, ext=ext), lang=a.lang)}
        if cache: pickle.dump(refs["cs_v5"], open(cache, "wb"))
    print("cs_v5 files hashed (language: " + a.lang + "):", refs["cs_v5"]["files"], f"({time.time()-t0:.0f}s)", flush=True)
    plan = []
    for item in a.sources.split(","):
        plan.append(parse_item(item))
    for name, lim in plan:
        if lim is None:
            refs[name] = build_sets(stream_source(name), lang=a.lang); print(name, "hashed fully:", refs[name]["files"], flush=True)
    report = {"cs_v5_java_files": refs["cs_v5"]["files"], "sources": {}}
    for name, lim in plan:
        r = report["sources"][name] = {"sample": "ALL" if lim is None else lim, "vs": {}}
        for rn, ref in refs.items():
            if rn == name: continue
            r["vs"][rn] = overlap(stream_source(name, shuffle=lim is not None and not name.startswith("jsonl:")), ref, lim, a.lang)
        print(name, json.dumps(r), flush=True)
    json.dump(report, open(os.path.expanduser(a.out), "w"), indent=1)
    print("saved", a.out)


if __name__ == "__main__":
    main()
