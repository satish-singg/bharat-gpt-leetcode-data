#!/usr/bin/env python3
"""Run LeetCode statement examples against Java `class Solution` code. Many solutions are compiled in ONE javac call (each in its own package pK)
and run in ONE JVM (driver with a per-solution timeout) - about 100 solutions per 10 s on one core.
Supported parameter/return types: int/long/double/boolean/char/String, arrays of them (also 2-D), List<...> of them (also nested). Everything else (ListNode, TreeNode, Node, Map, void ...) is skipped (tier C).
  run(jobs) with jobs = [{"id","code","examples":[(args_dict, expected)], "hint": method_name_or_None}] -> {id: {"total","passed","unordered","error","firsterr"}}"""
import json, os, re, shutil, subprocess, sys, tempfile

class Unsupported(Exception): pass
PRIM = {"int", "Integer", "short", "byte", "long", "Long", "double", "Double", "boolean", "Boolean", "char", "Character", "String"}

def split_params(s):
    out, d, cur = [], 0, ""
    for ch in s:
        if ch == "<": d += 1
        elif ch == ">": d -= 1
        if ch == "," and d == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

def find_method(code, hint):
    i = code.find("class Solution"); body = code[i:] if i >= 0 else code
    found = []
    for m in re.finditer(r"^[ \t]*((?:public|private|protected)\s+)?((?:static|final)\s+)*([\w<>\[\],\s\?]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws[^{]*)?\{", body, flags=re.M):
        ret, name = m.group(3).strip(), m.group(4)
        if name in ("if", "for", "while", "switch", "catch", "synchronized", "Solution") or ret.split()[-1] in ("new", "return", "else", "throw"): continue
        found.append((bool(m.group(1) and "public" in m.group(1)), ret, name, split_params(m.group(5))))
    if hint:
        for pub, ret, name, params in found:
            if name.lower() == hint.lower(): return ret, name, params
    for pub, ret, name, params in found:
        if pub: return ret, name, params
    return found[0][1:] if found else None

def supported(t):
    t = t.replace("final ", "").strip()
    while t.endswith("[]"): t = t[:-2].strip()
    m = re.match(r"^(?:List|ArrayList)<(.+)>$", t)
    return supported(m.group(1)) if m else t in PRIM

def jlit(t, v):
    t = t.replace("final ", "").strip()
    if t.endswith("[]"):
        inner = t[:-2].strip(); return "new %s[]{%s}" % (inner, ",".join(jlit(inner, x) for x in v))
    m = re.match(r"^(?:List|ArrayList)<(.+)>$", t)
    if m:
        inner = m.group(1).strip(); return "new ArrayList<%s>(Arrays.asList(%s))" % (inner, ",".join(jlit(inner, x) for x in v)) if v else "new ArrayList<%s>()" % inner
    if t in ("int", "Integer", "short", "byte"): return str(int(v))
    if t in ("long", "Long"): return "%dL" % int(v)
    if t in ("double", "Double"): return repr(float(v))
    if t in ("boolean", "Boolean"): return "true" if v else "false"
    if t in ("char", "Character"): return "(char)%d" % ord(str(v)[0])
    if t == "String": return json.dumps(v)
    raise Unsupported(t)

SHOW = r'''
    static String show(Object o) {
        if (o == null) return "null";
        if (o instanceof String) return jq((String) o);
        if (o instanceof Character) return jq(String.valueOf(o));
        if (o instanceof Boolean || o instanceof Integer || o instanceof Long || o instanceof Short || o instanceof Byte) return o.toString();
        if (o instanceof Double || o instanceof Float) { double d = ((Number) o).doubleValue(); return Double.isNaN(d) || Double.isInfinite(d) ? "null" : Double.toString(d); }
        StringBuilder sb = new StringBuilder("[");
        if (o.getClass().isArray()) { int n = java.lang.reflect.Array.getLength(o); for (int i = 0; i < n; i++) { if (i > 0) sb.append(","); sb.append(show(java.lang.reflect.Array.get(o, i))); } }
        else if (o instanceof Iterable) { boolean f = true; for (Object x : (Iterable<?>) o) { if (!f) sb.append(","); f = false; sb.append(show(x)); } }
        else return jq(o.toString());
        return sb.append("]").toString();
    }
    static String jq(String s) { StringBuilder b = new StringBuilder("\""); for (char c : s.toCharArray()) { if (c == '"' || c == '\\') b.append('\\').append(c); else if (c < 32 || c > 126) b.append(String.format("\\u%04x", (int) c)); else b.append(c); } return b.append("\"").toString(); }
'''
DRIVER = r'''
import java.util.*;
public class Driver {
    public static void main(String[] a) throws Exception {
        for (String p : a) {
            final String[] res = new String[1];
            Thread t = new Thread(null, () -> { try { res[0] = (String) Class.forName(p + ".Main").getMethod("run").invoke(null); } catch (Throwable e) { Throwable c = e.getCause() != null ? e.getCause() : e; res[0] = "EXC " + c.getClass().getSimpleName(); } }, "w", 256L << 20);
            t.setDaemon(true); t.start(); t.join(6000);
            System.out.println("@@BEGIN " + p);
            System.out.println(t.isAlive() ? "TIMEOUT" : res[0]);
            System.out.println("@@END");
            System.out.flush();
        }
        System.exit(0);
    }
}
'''

def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try: return abs(a - b) <= 1e-4 * max(1, abs(b))
        except Exception: return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)): return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b

def canon(x):
    if isinstance(x, (list, tuple)):
        try: return sorted((canon(i) for i in x), key=lambda v: json.dumps(v, sort_keys=True, default=str))
        except Exception: return x
    return x

def prepare(job, root, k):
    mm = find_method(job["code"], job.get("hint"))
    if not mm: raise Unsupported("no_method")
    ret, name, params = mm
    if ret.strip() == "void" or not supported(ret): raise Unsupported("ret " + ret)
    ptypes = []
    for p in params:
        p = p.strip(); t = re.sub(r"\s+\w+$", "", p).replace("final ", "").strip()
        if not supported(t): raise Unsupported(t)
        ptypes.append(t)
    calls = []
    for args, exp in job["examples"]:
        vals = list(args.values())
        if len(vals) != len(ptypes): raise Unsupported("arity")
        calls.append("try { sb.append(show(s.%s(%s))).append('\\n'); } catch (Throwable e) { sb.append(\"EXC \" + e.getClass().getSimpleName()).append('\\n'); }" % (name, ",".join(jlit(t, v) for t, v in zip(ptypes, vals))))
    d = os.path.join(root, "p%d" % k); os.makedirs(d)
    code = re.sub(r"^package [^\n]*\n", "", job["code"], flags=re.M)
    open(os.path.join(d, "Solution.java"), "w").write("package p%d;\nimport java.util.*;\nimport java.util.stream.*;\nimport java.util.function.*;\n%s\n" % (k, code))
    open(os.path.join(d, "Main.java"), "w").write("package p%d;\nimport java.util.*;\npublic class Main {\n%s\n    public static String run() {\n        StringBuilder sb = new StringBuilder(); Solution s = new Solution();\n        %s\n        return sb.toString();\n    }\n}\n" % (k, SHOW, "\n        ".join(calls)))

def run_batch(jobs, base):
    root = tempfile.mkdtemp(prefix="jx", dir=base); res = {}; ok = []
    for k, job in enumerate(jobs):
        try: prepare(job, root, k); ok.append((k, job))
        except Unsupported as e: res[job["id"]] = {"skip": str(e)}
        except Exception as e: res[job["id"]] = {"skip": "prep:" + type(e).__name__}
    open(os.path.join(root, "Driver.java"), "w").write(DRIVER)
    out = os.path.join(root, "out"); os.makedirs(out)
    for attempt in range(4):
        files = [os.path.join(root, "p%d" % k, f) for k, _ in ok for f in ("Solution.java", "Main.java")] + [os.path.join(root, "Driver.java")]
        r = subprocess.run(["javac", "-nowarn", "-proc:none", "-J-Xmx1g", "-d", out] + files, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
        if r.returncode == 0: break
        bad = set(int(x) for x in re.findall(r"/p(\d+)/(?:Solution|Main)\.java:\d+: error", r.stderr))
        if not bad: ok = []; break
        for k, job in ok:
            if k in bad: res[job["id"]] = {"skip": "compile_error", "firsterr": ""}
        ok = [(k, j) for k, j in ok if k not in bad]
    if ok:
        try:
            r = subprocess.run(["java", "-Xmx1g", "-Xss64m", "-cp", out, "Driver"] + ["p%d" % k for k, _ in ok], capture_output=True, text=True, timeout=60 + 8 * len(ok), stdin=subprocess.DEVNULL)
            text = r.stdout
        except subprocess.TimeoutExpired as e:
            text = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        got = {m.group(1): m.group(2) for m in re.finditer(r"@@BEGIN (p\d+)\n(.*?)\n?@@END", text, flags=re.S)}
        for k, job in ok:
            o = got.get("p%d" % k)
            if o is None: res[job["id"]] = {"total": len(job["examples"]), "passed": 0, "unordered": 0, "error": "NoOutput"}; continue
            if o.strip() == "TIMEOUT": res[job["id"]] = {"total": len(job["examples"]), "passed": 0, "unordered": 0, "error": "TimeoutError"}; continue
            lines = o.split("\n"); passed = unord = 0; first = None
            for (args, exp), line in zip(job["examples"], lines):
                if line.startswith("EXC"): first = first or line; continue
                try: val = json.loads(line)
                except Exception: first = first or "badjson"; continue
                if close(val, exp): passed += 1
                elif close(canon(val), canon(exp)): unord += 1
            res[job["id"]] = {"total": len(job["examples"]), "passed": passed, "unordered": unord, "error": None, "firsterr": first}
    shutil.rmtree(root, ignore_errors=True)
    return res

def run(jobs, batch=80, base=None):
    base = base or tempfile.mkdtemp(prefix="jbase"); out = {}
    for i in range(0, len(jobs), batch):
        try: out.update(run_batch(jobs[i:i + batch], base))
        except Exception as e:
            for j in jobs[i:i + batch]: out[j["id"]] = {"skip": "batch_error:" + type(e).__name__}
        print("java examples", min(i + batch, len(jobs)), "/", len(jobs), file=sys.stderr, flush=True)
    return out
