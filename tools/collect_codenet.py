#!/usr/bin/env python3
"""Project CodeNet (the ORIGINAL release, AIZU + AtCoder submissions) -> pipeline JSONL of ACCEPTED solutions, with problem-level decontamination.  CPU only, nothing is executed.

  python3 tools/collect_codenet.py inspect --root ~/Downloads/Project_CodeNet                       # layout, languages, status counts: run this FIRST
  python3 tools/collect_codenet.py collect --root ~/Downloads/Project_CodeNet --lang Java --max-per-problem 10 \
      --locked ~/ProjectAI/data/test/locked_eval_1365.jsonl --out ~/ProjectAI/data/java/codenet_java.jsonl
  (--lang Python likewise.  Resumable: doc_ids already in --out are skipped.)

Assumed layout (from the CodeNet paper/README; `inspect` prints what is really there):  <root>/data/<problem_id>/<Language>/<submission_id>.<ext>,
<root>/metadata/<problem_id>.csv (columns include submission_id, language, status, cpu_time, memory, code_size), <root>/problem_descriptions/<problem_id>.html.
What it does: keeps only status == "Accepted"; at most --max-per-problem solutions per problem (chosen by a hash of the submission id, not by date or size, with identical
normalised code kept once); drops files < 40 or > 30,000 characters; Python must pass ast.parse (this also removes Python 2); and DECONTAMINATES: AtCoder and AIZU
problems appear in TACO/CodeContests, which feed the locked evaluation tracks, so a problem is excluded entirely when its statement shares >= 20% of a locked prompt's 8-grams
(tools/build_sft_corpus.overlap_reason), and a single solution is excluded when it shares a distinctive 13-gram with a locked reference solution.
Output: {"text": code, "source": "code_contest_codenet_<lang>", "license": "codenet-research", "doc_id": "codenet:<problem>:<submission>", "prov": {...}}."""
import argparse, ast, collections, csv, hashlib, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WS = re.compile(r"\s+")
TAG = re.compile(r"<[^>]+>")


def html_text(s):
    return WS.sub(" ", html.unescape(TAG.sub(" ", re.sub(r"(?is)<(script|style).*?</\1>", " ", s)))).strip()


def norm_code(t):
    return WS.sub(" ", t).strip()


def pick(submissions, k):
    """deterministic spread: sort by hash of the submission id, keep k, one per distinct normalised code (caller passes (sid, code))."""
    seen, out = set(), []
    for sid, code in sorted(submissions, key=lambda x: hashlib.sha1(x[0].encode()).hexdigest()):
        h = hashlib.sha1(norm_code(code).encode("utf-8", "ignore")).hexdigest()
        if h in seen: continue
        seen.add(h); out.append((sid, code))
        if len(out) >= k: break
    return out


def accepted_ids(meta_csv, lang):
    ids = {}
    if not os.path.exists(meta_csv): return ids
    with open(meta_csv, newline="", encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            if (r.get("status") or "").strip() == "Accepted" and (r.get("language") or "").strip().lower() == lang.lower():
                ids[r["submission_id"]] = r
    return ids


def already(out):
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            for line in f:
                try: done.add(json.loads(line)["doc_id"])
                except Exception: pass
    return done


def collect(root, lang, max_per, out, check=None, min_chars=40, max_chars=30000, log=print):
    """check(description_text, code) -> reason or None (reason on description-only call: code == "")."""
    data = os.path.join(root, "data"); meta = os.path.join(root, "metadata"); desc_dir = os.path.join(root, "problem_descriptions")
    done = already(out); stats = collections.Counter(); stats["already"] = len(done)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        for pid in sorted(os.listdir(data)):
            ldir = next((os.path.join(data, pid, d) for d in os.listdir(os.path.join(data, pid)) if d.lower() == lang.lower()), None) if os.path.isdir(os.path.join(data, pid)) else None
            if not ldir: continue
            stats["problems_with_lang"] += 1
            dpath = os.path.join(desc_dir, pid + ".html"); desc = html_text(open(dpath, encoding="utf-8", errors="ignore").read()) if os.path.exists(dpath) else ""
            if check and desc and check(desc, ""):
                stats["problem_excluded_locked_overlap"] += 1; continue
            ok = accepted_ids(os.path.join(meta, pid + ".csv"), lang)
            subs = []
            for fn in os.listdir(ldir):
                sid = fn.rsplit(".", 1)[0]
                if sid not in ok: continue
                try: code = open(os.path.join(ldir, fn), encoding="utf-8", errors="ignore").read()
                except OSError: continue
                if not (min_chars <= len(code) <= max_chars): stats["bad_length"] += 1; continue
                if lang.lower() == "python":
                    try: ast.parse(code)
                    except (SyntaxError, ValueError, MemoryError, RecursionError): stats["python_syntax_or_py2"] += 1; continue
                subs.append((sid, code))
            for sid, code in pick(subs, max_per):                       # the choice is deterministic, so a re-run selects the same files and only skips those already written
                if f"codenet:{pid}:{sid}" in done: continue
                if check and desc and check(desc, code): stats["solution_excluded_locked_overlap"] += 1; continue
                f.write(json.dumps({"text": code, "source": f"code_contest_codenet_{lang.lower()}", "license": "codenet-research", "doc_id": f"codenet:{pid}:{sid}",
                                    "prov": {"problem": pid, "status": "Accepted"}}, ensure_ascii=False) + "\n"); stats["written"] += 1
    return dict(stats)


def inspect(root, sample=30):
    print("top level:", sorted(os.listdir(root))[:20])
    data = os.path.join(root, "data")
    if os.path.isdir(data):
        pids = sorted(os.listdir(data)); print("problems in data/:", len(pids), "first", pids[:5])
        langs = collections.Counter()
        for pid in pids[:200]:
            p = os.path.join(data, pid)
            if os.path.isdir(p):
                for d in os.listdir(p): langs[d] += 1
        print("language folders in the first 200 problems:", langs.most_common(12))
    meta = os.path.join(root, "metadata")
    if os.path.isdir(meta):
        files = sorted(os.listdir(meta)); print("metadata files:", len(files), files[:4])
        st = collections.Counter(); cols = None
        for fn in files[:sample]:
            if not fn.endswith(".csv") or fn.startswith("problem_list"): continue
            with open(os.path.join(meta, fn), newline="", encoding="utf-8", errors="ignore") as f:
                rd = csv.DictReader(f); cols = cols or rd.fieldnames
                for r in rd: st[(r.get("language"), r.get("status"))] += 1
        print("columns:", cols); print("(language, status) counts in the first", sample, "metadata files:", st.most_common(12))
    d = os.path.join(root, "problem_descriptions"); print("problem_descriptions:", len(os.listdir(d)) if os.path.isdir(d) else "MISSING")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect"); i.add_argument("--root", required=True)
    c = sub.add_parser("collect"); c.add_argument("--root", required=True); c.add_argument("--lang", required=True, choices=["Java", "Python", "C++"])
    c.add_argument("--max-per-problem", type=int, default=10); c.add_argument("--out", required=True); c.add_argument("--locked", default=None)
    a = ap.parse_args()
    root = os.path.expanduser(a.root)
    if a.cmd == "inspect": return inspect(root)
    check = None
    if a.locked:
        import build_sft_corpus as B
        locked = B.load_locked(a.locked); check = lambda desc, code: B.overlap_reason(desc, code, locked)
    else:
        print("NOTE: no --locked: overlap with the locked tasks is NOT checked. Do not train on this file.")
    print(json.dumps(collect(root, a.lang, a.max_per_problem, os.path.expanduser(a.out), check)))


if __name__ == "__main__":
    main()
