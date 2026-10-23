#!/usr/bin/env python3
"""Checker for reasoning notes. Used by ChatGPT before every commit and by us before training.

  python3 tools/validate_notes.py --solutions data/solutions/batch_0060.jsonl [more files]     # notes inside solution records (new batches)
  python3 tools/validate_notes.py --in fixnotes/in --out fixnotes/out                          # fix task: out lines {"id","notes","complexity_reason"} joined to in lines by id
Exit code 1 and a list of problems when anything fails. A record passes only if ALL of these hold:
  1. `notes` is exactly six lines starting with the labels: Task and constraints / Idea / Technique and why it applies / Invariant / Edge cases / Complexity
  2. 60-220 words in total; no chat words (wait, hmm, let's), no code blocks, no markdown
  3. none of the known template sentences (see BANNED) and no meta talk about tests ("local tests", "self-check")
  4. the Invariant line is not a copy or near copy of the Idea line
  5. the notes use at least one real name from THIS code (a variable, method or helper, also as separate words: findClosestElements -> closest elements)
  6. the Complexity line contains O( (or says 'not established') and the Edge cases line has at least 8 words
  7. no Technique / Invariant / Edge cases line is identical to the same line of a different problem (a line may repeat between the Python and the Java record of the SAME problem)
"""
import argparse, glob, json, os, re, sys, collections

LAB = ["Task and constraints:", "Idea:", "Technique and why it applies:", "Invariant:", "Edge cases:", "Complexity:"]
BANNED = [r"six local tests", r"local tests?", r"self[- ]check", r"where permitted, boundaries", r"maintained accumulator", r"preserve (all )?(the )?information (needed|required)",
          r"minimal structures", r"relevant boundaries", r"handled as relevant", r"\bTask: Solve\b", r"empty or singleton inputs where permitted",
          r"stack, dp state, sorted ordering", r"\b(wait|hmm)\b", r"let'?s think", r"as an ai", r"```", r"^#"]
STOP = set("""self cls return class def int str list dict set bool float long void public private static final new null none true false else elif while for if not and or the len range
import from print this that with lambda pass break continue try except raise yield del global nonlocal assert string integer boolean double char byte short object array arrays
List ArrayList HashMap HashSet Map Set Math Integer String System Solution Optional Override""".split())


def words(s): return re.findall(r"\S+", s)
def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
def jacc(a, b):
    a, b = set(norm(a).split()), set(norm(b).split()); return len(a & b) / max(1, len(a | b))
def idents(code):
    """identifiers of the code plus their camelCase / snake_case parts (findClosestElements -> find, closest, elements)"""
    out = set()
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", code):
        if w in STOP or w.lower() in STOP: continue
        out.add(w)
        for part in re.findall(r"[A-Z]?[a-z]{4,}|[A-Z]{2,}(?![a-z])|\d+", w.replace("_", " ")):
            if part.lower() not in STOP: out.add(part)
    return out


def check(rec, code=None):
    """returns a list of problems for one record (rec has `notes`; code from rec or the argument)"""
    n = rec.get("notes", ""); probs = []; lines = n.split("\n")
    if not (len(lines) == 6 and all(x.startswith(y) for x, y in zip(lines, LAB))): return ["not exactly six lines with the six labels in order"]
    w = len(words(n))
    if not 60 <= w <= 220: probs.append(f"{w} words (need 60-220)")
    for pat in BANNED:
        if re.search(pat, n, re.I | re.M): probs.append(f"banned phrase /{pat}/")
    idea, inv, edge, comp = (lines[i].split(":", 1)[1].strip() for i in (1, 3, 4, 5))
    if jacc(idea, inv) > 0.6: probs.append("Invariant repeats the Idea line")
    if "O(" not in comp and "not established" not in comp.lower(): probs.append("Complexity line has no O(...)")
    if len(words(edge)) < 8: probs.append("Edge cases line shorter than 8 words")
    code = code if code is not None else rec.get("code", "")
    ids = idents(code)
    if ids:
        hit = sum(1 for i in ids if re.search(re.escape(i), n, re.I if len(i) > 3 else 0))
        if hit < 1: probs.append(f"the notes use none of the names in this code - describe THIS code (its variables, helper methods, data structures)")
    return probs


TEMPLATE_REASON = re.compile(r"bounded number of times|algorithm's stack, DP, or collection state|each input element or state", re.I)


def check_reason(rec):
    """fix-task output also carries complexity_reason: one specific sentence"""
    cr = rec.get("complexity_reason") or ""
    return ["complexity_reason missing, shorter than 8 words, or the old template sentence"] if (len(cr.split()) < 8 or TEMPLATE_REASON.search(cr)) else []


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solutions", nargs="*", default=[]); ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    ap.add_argument("--all-lines-index", default="data/solutions", help="folder whose notes are used for the cross-record duplicate-line test")
    a = ap.parse_args()
    recs = []                                                     # (label, problem key, record, code)
    for p in sum((glob.glob(x) for x in a.solutions), []):
        for r in load(p): recs.append((f"{os.path.basename(p)} {r['number']}:{r['language']}", r["number"], r, r.get("code", "")))
    if a.inp and a.out:
        code = {}
        for p in glob.glob(os.path.join(a.inp, "*.jsonl")):
            for r in load(p): code[r["id"]] = r
        for p in sorted(glob.glob(os.path.join(a.out, "*.jsonl"))):
            for r in load(p):
                src = code.get(r["id"])
                if not src: recs.append((f"{os.path.basename(p)} {r.get('id')}", None, r, "")); continue
                recs.append((f"{os.path.basename(p)} {r['id']}", src["number"], r, src["code"]))
    bad = 0; seen = collections.defaultdict(set)                  # normalised line -> problem numbers using it
    for lab, num, r, code in recs:
        for ln in r.get("notes", "").split("\n")[2:5]: seen[norm(ln.split(":", 1)[-1])].add(num)
    for lab, num, r, code in recs:
        probs = check(r, code) + (check_reason(r) if a.inp else [])
        for ln in r.get("notes", "").split("\n")[2:5]:
            if len(seen[norm(ln.split(":", 1)[-1])]) > 1: probs.append(f"line also used for another problem: {ln[:70]}..."); break
        if probs: bad += 1; print("FAIL", lab, "|", "; ".join(probs)[:260])
    print(f"checked {len(recs)} records, {bad} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
