#!/usr/bin/env python3
"""Near-duplicate and method-in-file checks for Java sources (CPU only, read-only). Complements tools/java_overlap.py, which only sees IDENTICAL files.

  python3 tools/java_dedup_probe.py --cs-train ~/cs-data/cs-v5/clean/train.jsonl --out ~/java_dedup.json \
      --full stack_java_clean --probe starcoderdata:20000,java_code_large:20000 --methods nando_csn:20000,cornstack:20000 \
      [--cache ~/cs_v5_java_dedup.pkl]

Method (approximate, documented in docs/JAVA_SOURCES.md):
  * "distinctive line" = a line of >= 25 characters after removing comments and collapsing whitespace, excluding package/import lines.
  * NEAR-DUPLICATE sketch of a file = its 8 smallest 64-bit line hashes (bottom-k). Two files that share >= 6 of 8 sketch values are
    reported as near-duplicates (roughly Jaccard >= 0.75 on their distinctive lines). Files with < 4 distinctive lines are "too small to judge".
    This is an estimate for planning, not the final dedup (that stays the pipeline's own near-dup pass).
  * METHOD IN FILE: a method (CodeSearchNet / CornStack row) counts as "contained" when >= 90% of its distinctive lines (at least 3) occur in
    the line set of the reference files (cs-v5 Java + every --full source). Line-set matching ignores line ORDER, so it is an upper-ish estimate.
--full sources are hashed completely and inserted into the index (the first copy of a near-duplicate group counts as the original; later copies are
counted as internal near-duplicates). --probe sources are only compared, never inserted, and are read shuffled with a fixed seed.
"""
import argparse, array, hashlib, json, os, pickle, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from java_overlap import iter_cs_java, COMMENT, stream_source   # reuse the cs-v5 reader, comment regex and source loaders

K, T, MIN_LINES, MIN_LEN = 8, 6, 4, 25


def distinct_hashes(text):
    """sorted unique 64-bit hashes of the distinctive lines of a Java file/method."""
    out = set()
    for ln in COMMENT.sub(" ", text).split("\n"):
        ln = " ".join(ln.split())
        if len(ln) < MIN_LEN or ln.startswith(("package ", "import ")):
            continue
        out.add(int(hashlib.sha1(ln.encode("utf-8", "replace")).hexdigest()[:16], 16))
    return sorted(out)


class NearDupIndex:
    def __init__(self):
        self.map = {}          # sketch value -> id of the first file that had it
        self.n = 0

    def query(self, hashes):
        """(status, id): status in 'small' (too few lines), 'dup' (near-duplicate of file id), 'new'."""
        if len(hashes) < MIN_LINES:
            return "small", None
        sk = hashes[:K]
        votes = {}
        for v in sk:
            j = self.map.get(v)
            if j is not None:
                votes[j] = votes.get(j, 0) + 1
        need = min(T, len(sk))
        best = max(votes.items(), key=lambda kv: kv[1], default=(None, 0))
        return ("dup", best[0]) if best[1] >= need else ("new", None)

    def add(self, hashes):
        fid = self.n; self.n += 1
        for v in hashes[:K]:
            self.map.setdefault(v, fid)
        return fid


class LineSet:
    """all distinctive-line hashes of the reference files, as a sorted numpy array for fast membership."""
    def __init__(self):
        self.buf = array.array("Q"); self.arr = None

    def add(self, hashes):
        self.buf.extend(hashes)

    def freeze(self):
        import numpy as np
        self.arr = np.unique(np.frombuffer(self.buf, dtype=np.uint64)); self.buf = None
        return self

    def contained(self, hashes, frac=0.9, min_lines=3):
        import numpy as np
        if len(hashes) < min_lines:
            return None
        h = np.array(hashes, dtype=np.uint64)
        idx = np.searchsorted(self.arr, h)
        idx[idx == len(self.arr)] = 0
        return float((self.arr[idx] == h).mean()) >= frac


def probe(texts, index, limit=None):
    n = dup = small = 0
    for t in texts:
        if limit is not None and n >= limit: break
        if not t: continue
        n += 1
        st, _ = index.query(distinct_hashes(t))
        dup += st == "dup"; small += st == "small"
    judged = n - small
    return {"files": n, "too_small_to_judge": small, "near_dup_of_reference": dup,
            "near_dup_rate_of_judged": round(dup / judged, 4) if judged else None}


def methods_in_files(texts, lines, limit=None):
    n = inside = small = 0
    for t in texts:
        if limit is not None and n >= limit: break
        if not t: continue
        n += 1
        c = lines.contained(distinct_hashes(t))
        if c is None: small += 1
        elif c: inside += 1
    judged = n - small
    return {"methods": n, "too_small_to_judge": small, "contained_in_reference_files": inside,
            "contained_rate_of_judged": round(inside / judged, 4) if judged else None}


def method_text(name):
    """query/docstring + code text for a method-level source."""
    from datasets import load_dataset
    if name == "nando_csn":
        return ((r.get("code") or "") for r in load_dataset("Nan-Do/code-search-net-java", split="train", streaming=True).shuffle(seed=0, buffer_size=10000))
    if name == "cornstack":
        return ((r.get("document") or "") for r in load_dataset("nomic-ai/cornstack-java-v1", split="train", streaming=True).shuffle(seed=0, buffer_size=10000))
    raise SystemExit("unknown method source " + name)


def parse(spec):
    out = []
    for item in [s for s in spec.split(",") if s.strip()]:
        name, _, lim = item.strip().partition(":")
        out.append((name, int(lim) if lim and lim.upper() != "ALL" else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cs-train", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--full", default="stack_java_clean"); ap.add_argument("--probe", default=""); ap.add_argument("--methods", default="")
    ap.add_argument("--cache", help="pickle of the cs-v5 index + line set (slow to build once)")
    a = ap.parse_args()
    t0 = time.time()
    cache = os.path.expanduser(a.cache) if a.cache else None
    index, lines = NearDupIndex(), LineSet()
    if cache and os.path.exists(cache):
        index, lines = pickle.load(open(cache, "rb"))
    else:
        for i, t in enumerate(iter_cs_java(a.cs_train, progress=True)):
            if not t: continue
            h = distinct_hashes(t); index.add(h); lines.add(h)
        print(f"cs-v5 Java indexed: {index.n:,} files ({time.time()-t0:.0f}s)", flush=True)
        if cache: pickle.dump((index, lines), open(cache, "wb"))
    n_cs = index.n
    report = {"cs_v5_files": n_cs, "full": {}, "probe": {}, "methods": {}}
    for name, _ in parse(a.full):
        n = dup_cs = dup_self = small = 0
        for t in stream_source(name):
            if not t: continue
            n += 1
            h = distinct_hashes(t)
            st, j = index.query(h)
            if st == "small": small += 1
            elif st == "dup":
                if j < n_cs: dup_cs += 1
                else: dup_self += 1
            if st != "dup": index.add(h)
            lines.add(h)
            if n % 100000 == 0: print(f"  {name}: {n:,} files", flush=True)
        judged = n - small
        report["full"][name] = {"files": n, "too_small_to_judge": small, "near_dup_of_cs_v5": dup_cs, "near_dup_of_earlier_file_in_same_source": dup_self,
                                "near_dup_rate_cs_v5": round(dup_cs / judged, 4), "near_dup_rate_internal": round(dup_self / judged, 4)}
        print(name, json.dumps(report["full"][name]), flush=True)
    for name, lim in parse(a.probe):
        report["probe"][name] = probe(stream_source(name, shuffle=True), index, lim or 20000)
        print(name, json.dumps(report["probe"][name]), flush=True)
    if a.methods:
        if lines.arr is None: lines.freeze()
        for name, lim in parse(a.methods):
            report["methods"][name] = methods_in_files(method_text(name), lines, lim or 20000)
            print(name, json.dumps(report["methods"][name]), flush=True)
    json.dump(report, open(os.path.expanduser(a.out), "w"), indent=1)
    print("saved", a.out)


if __name__ == "__main__":
    main()
