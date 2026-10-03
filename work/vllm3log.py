import json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
b = pathlib.Path("work/vllm3_log.json").read_bytes()
t = None
for enc in ("utf-16","utf-16-le","utf-8"):
    try:
        x = b.decode(enc)
        if "PROBE v3" in x or "gpu:" in x: t = x; break
    except Exception: pass
if t is None: print("decode fail:", b[:400]); raise SystemExit
i = t.find("[")
try:
    j = json.loads(t[i:]); txt = "".join(e.get("data","") for e in j)
except Exception: txt = t
keep = ("VERDICT","wheels; tags","vllm-","SAMPLE","import failed","IMPORTED","pip rc","NOT MOUNTED","---")
for line in txt.split("\n"):
    s = line.rstrip()
    if s.strip() and any(k in s for k in keep): print("  | %s" % s[:180])
