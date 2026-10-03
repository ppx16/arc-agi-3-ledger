import json, sys, pathlib, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
b = pathlib.Path("work/probe_log.json").read_bytes()
t = None
for enc in ("utf-16","utf-16-le","utf-8"):
    try:
        x = b.decode(enc)
        if "GPU PROBE" in x: t = x; break
    except Exception: pass
if t is None:
    print("could not decode; raw head:"); print(b[:400]); raise SystemExit
i = t.find("[")
try:
    j = json.loads(t[i:]); txt = "".join(e.get("data","") for e in j)
except Exception:
    txt = t
for line in txt.split("\n"):
    if any(k in line for k in ("GPU PROBE","machine:","nvidia-smi","dev0","dev1","torch:","cc=","END","Error","error")):
        print("  | %s" % line.strip()[:180])
