import json, re, sys
n = int(sys.argv[1]); rows = [json.loads(l) for l in open("annotate/batch_%04d.jsonl" % n)]
for k, r in enumerate(rows, 1):
    st = r["statement"]; i = st.find("Constraints:")
    head = re.sub(r"\n+", " ", st[:(i if i > 0 else 300)])[:260]; cons = re.sub(r"\s+", " ", st[i:])[:220] if i > 0 else ""
    print("## %d | %s | T=%s S=%s (%s)\n%s\n%s\n```\n%s```" % (k, r["title"], r["time_complexity"], r["space_complexity"], r["id"].split(":", 1)[1], head, cons, re.sub(r"\n\s*\n", "\n", re.sub(r"^\s*#.*\n", "", r["code"], flags=re.M))))
