#!/usr/bin/env python3
"""CPU-only pilot: stream a few thousand rows from each candidate Java source and measure what we would actually get.
Read-only, downloads only the streamed rows, never runs anything. Prints and saves a JSON report.

  python3 tools/java_pilot.py --tokenizer ~/cs-data/cs-v5/tok/tokenizer.json --limit 5000 --out ~/java_pilot.json \
      --sources cornstack,java_code_large,starcoderdata,stack_java_clean,nando_csn,nemotron,code_contests

Gated sets (starcoderdata, nemotron) need you to accept the terms on the HF page, and HF_TOKEN set in the SAME terminal
(typed there, never pasted in chat). A source that fails is reported as an error and the others still run.
`nemotron` needs --nemotron-config NAME (the card does not give config names): run once without it and read the error.
Any other dataset: --sources hf:REPO[:CONFIG]:FIELD (generic text field; 'no_java_keywords_rate' is then meaningless).
Reported per source: columns seen, rows, tokens/row, exact-duplicate rate, size spread, license-header rate, tiny-file rate,
non-ASCII rate, share too long for the 2,048 context, 3 random previews. Sizes of external cards are NOT trusted: only these numbers are.
"""
import argparse, hashlib, json, os, random, re, sys, time

HDR = re.compile(r"licensed under|copyright|all rights reserved|permission is hereby granted", re.I)
JAVAISH = re.compile(r"\b(class|interface|enum|record)\s+\w+|\bpackage\s+[\w.]+;|\bimport\s+[\w.*]+;")


def analyze(texts, tokenizer=None, limit=5000, max_tokens=1900, seed=0, n_prev=3):
    """texts: iterable of str (None/empty are counted as empty). Returns a stats dict."""
    seen, n, empty, dup, hdr, tiny, nonascii, notjava, toolong, nonempty = set(), 0, 0, 0, 0, 0, 0, 0, 0, 0
    chars, toks, prev = [], [], []
    rnd = random.Random(seed)
    for t in texts:
        if n >= limit:
            break
        n += 1
        if not t or not t.strip():
            empty += 1
            continue
        h = hashlib.sha1(" ".join(t.split()).encode("utf-8", "replace")).hexdigest()
        if h in seen:
            dup += 1
        seen.add(h)
        chars.append(len(t))
        if len(t) < 200: tiny += 1
        if HDR.search(t[:600]): hdr += 1
        if sum(ord(c) > 127 for c in t[:4000]) > 0.05 * min(len(t), 4000): nonascii += 1
        if not JAVAISH.search(t): notjava += 1
        if tokenizer is not None:
            k = len(tokenizer.encode(t).ids)
            toks.append(k)
            if k > max_tokens: toolong += 1
        nonempty += 1                                   # reservoir sample of 3 previews over ALL non-empty rows read
        if len(prev) < n_prev: prev.append(t[:400])
        else:
            j = rnd.randrange(nonempty)
            if j < n_prev: prev[j] = t[:400]
    ok = len(chars)

    def pct(xs, q):
        s = sorted(xs)
        return s[min(len(s) - 1, int(q * len(s)))] if s else None
    out = {"rows_read": n, "rows_empty": empty, "rows_nonempty": ok,
           "exact_dup_rate": round(dup / ok, 4) if ok else None,
           "license_header_rate": round(hdr / ok, 4) if ok else None,
           "tiny_lt200chars_rate": round(tiny / ok, 4) if ok else None,
           "mostly_nonascii_rate": round(nonascii / ok, 4) if ok else None,
           "no_java_keywords_rate": round(notjava / ok, 4) if ok else None,
           "chars_p50_p90_max": [pct(chars, .5), pct(chars, .9), max(chars) if chars else None], "previews": prev}
    if toks:
        out.update(tokens_total=sum(toks), tokens_per_row_mean=round(sum(toks) / len(toks), 1),
                   tokens_p50_p90_max=[pct(toks, .5), pct(toks, .9), max(toks)], too_long_rate=round(toolong / len(toks), 4),
                   bytes_per_token=round(sum(chars) / sum(toks), 2),
                   unique_tokens_total=int(sum(toks) * (1 - dup / ok)) if ok else 0)
    return out


def code_contests_stats(rows, limit):
    """rows: iterable of CodeContests problems. Counts Java (language code 4) solutions; the card says 0 unknown, 1 py2, 2 c++, 3 py3, 4 java."""
    probs = with_java = jsol = jbad = n = 0
    for r in rows:
        if n >= limit: break
        n += 1
        s = r.get("solutions") or {}
        langs = s.get("language") or []
        k = sum(1 for x in langs if x == 4)
        b = sum(1 for x in ((r.get("incorrect_solutions") or {}).get("language") or []) if x == 4)
        probs += 1; jsol += k; jbad += b; with_java += 1 if k else 0
    return {"problems_read": probs, "problems_with_java_solution": with_java, "java_correct_solutions": jsol,
            "java_incorrect_solutions": jbad, "note": "train split only; counts from the streamed rows, scale to the full split yourself"}


def _stream(path, **kw):
    from datasets import load_dataset
    return load_dataset(path, split=kw.pop("split", "train"), streaming=True, **kw)


def source_texts(name, args):
    """(get_text, row iterator) for one source. `hf:REPO[:CONFIG]:FIELD` streams any public/gated HF dataset generically,
    e.g. hf:HuggingFaceTB/finemath:finemath-4plus:text  or  hf:open-web-math/open-web-math:text  (FIELD is required; rows are read shuffled with a fixed seed)."""
    if name.startswith("hf:"):
        parts = name[3:].split(":")
        repo, field = parts[0], parts[-1]
        kw = {"name": parts[1]} if len(parts) == 3 else {}
        return (lambda r: r.get(field)), _stream(repo, **kw).shuffle(seed=0, buffer_size=10000)
    if name == "cornstack":
        ds = _stream("nomic-ai/cornstack-java-v1")
        return (lambda r: (r.get("query") or "") + "\n\n" + (r.get("document") or "")), ds     # negatives are NOT used
    if name == "java_code_large":
        return (lambda r: r.get("code")), _stream("ajibawa-2023/Java-Code-Large")
    if name == "stack_java_clean":
        return (lambda r: r.get("content")), _stream("ammarnasr/the-stack-java-clean")
    if name == "nando_csn":
        return (lambda r: (r.get("docstring") or "") + "\n\n" + (r.get("code") or "")), _stream("Nan-Do/code-search-net-java")
    if name == "starcoderdata":
        return (lambda r: r.get("content")), _stream("bigcode/starcoderdata", data_dir="java")
    if name == "nemotron":
        if not args.nemotron_config:
            raise SystemExit("nemotron: pass --nemotron-config NAME (the card gives no config names)")
        ds = _stream("nvidia/Nemotron-Pretraining-Code-v2", name=args.nemotron_config)
        return (lambda r: r.get("content") if str(r.get("language", "java")).lower() == "java" else None), ds
    raise SystemExit("unknown source " + name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer"); ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--out", required=True); ap.add_argument("--sources", default="cornstack,java_code_large")
    ap.add_argument("--nemotron-config"); ap.add_argument("--max-tokens", type=int, default=1900)
    ap.add_argument("--previews", type=int, default=3, help="how many random previews (first 400 chars) to keep per source; 12 is better for judging quality")
    args = ap.parse_args()
    tk = None
    if args.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(os.path.expanduser(args.tokenizer))
    report = {"limit": args.limit, "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for name in [s.strip() for s in args.sources.split(",") if s.strip()]:
        t0 = time.time()
        try:
            if name == "code_contests":
                report[name] = code_contests_stats(_stream("deepmind/code_contests"), args.limit)
            else:
                get, ds = source_texts(name, args)
                cols = {}

                def gen():
                    for r in ds:
                        if not cols: cols["columns"] = sorted(r.keys())
                        yield get(r)
                report[name] = analyze(gen(), tk, args.limit, args.max_tokens, n_prev=args.previews)
                report[name]["columns"] = cols.get("columns")
        except BaseException as e:                       # one failing/gated source must not stop the others
            if isinstance(e, KeyboardInterrupt): raise
            report[name] = {"error": f"{type(e).__name__}: ...{str(e)[-700:]}"}
        report[name]["seconds"] = round(time.time() - t0, 1)
        print(name, json.dumps({k: v for k, v in report[name].items() if k != "previews"}, indent=1), flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(args.out))), exist_ok=True)
    json.dump(report, open(os.path.expanduser(args.out), "w"), indent=1)
    print("saved", args.out)


if __name__ == "__main__":
    main()
